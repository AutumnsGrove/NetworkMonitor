"""
Network monitoring daemon.

Main daemon loop that samples network usage every 5 seconds,
maps connections to processes, and stores data in database.
"""
import asyncio
import logging
import signal
import threading
from datetime import datetime
from typing import Optional, Dict, Set, Tuple
from collections import defaultdict

from src.process_mapper import ProcessMapper, ProcessInfo
from src.capture import NetworkCapture, PacketInfo, SCAPY_AVAILABLE
from src.db_queries import (
    insert_application, insert_network_sample,
    get_application_by_name, insert_domain, get_domain_by_name,
    insert_browser_domain_sample
)
from src.models import Application, NetworkSample, Domain, BrowserDomainSample
from src.retention import RetentionScheduler
from src.utils import get_domain_with_parent


logger = logging.getLogger(__name__)


class NetworkDaemon:
    """
    Main network monitoring daemon.

    Responsibilities:
    1. Sample network connections every N seconds
    2. Map connections to processes/applications
    3. Store samples in database
    4. Handle graceful shutdown
    """

    def __init__(
        self,
        sampling_interval: int = 5,
        enable_retention: bool = True,
        enable_packet_capture: bool = True
    ):
        """
        Initialize network daemon.

        Args:
            sampling_interval: Seconds between samples (default 5)
            enable_retention: Enable automatic data retention/aggregation
            enable_packet_capture: Enable scapy packet capture (requires sudo)
        """
        self.sampling_interval = sampling_interval
        self.enable_retention = enable_retention
        self.enable_packet_capture = enable_packet_capture
        self.running = False
        self.process_mapper = ProcessMapper()
        self.retention_scheduler: Optional[RetentionScheduler] = None
        self.network_capture: Optional[NetworkCapture] = None
        self._capture_thread: Optional[threading.Thread] = None

        # Track app_id mapping (cache for lookups)
        self.app_id_cache: Dict[str, int] = {}  # process_name -> app_id
        self.domain_id_cache: Dict[str, int] = {}  # domain -> domain_id

        # Active connections tracking
        self.active_connections: Dict[str, Set[int]] = defaultdict(set)

        # Packet tracking for byte calculations
        # Key: (dst_ip, dst_port), Value: {app_id, bytes_sent, bytes_received, packets, domains}
        self.connection_stats: Dict[Tuple[str, int], Dict] = defaultdict(lambda: {
            'app_id': None,
            'bytes_sent': 0,
            'bytes_received': 0,
            'packets_sent': 0,
            'packets_received': 0,
            'domains': set()
        })
        self._stats_lock = threading.Lock()

        # Statistics
        self.samples_collected = 0
        self.errors_count = 0
        self.packets_processed = 0

        logger.info(f"Initialized NetworkDaemon (interval: {sampling_interval}s, packet_capture: {enable_packet_capture})")

    async def start(self) -> None:
        """Start the daemon."""
        if self.running:
            logger.warning("Daemon already running")
            return

        logger.info("Starting network monitoring daemon")
        self.running = True

        # Start retention scheduler if enabled
        if self.enable_retention:
            self.retention_scheduler = RetentionScheduler()
            await self.retention_scheduler.start()

        # Start packet capture if enabled and available
        if self.enable_packet_capture and SCAPY_AVAILABLE:
            try:
                from src.capture import check_capture_permissions

                if not check_capture_permissions():
                    logger.warning("Packet capture requires root privileges - running as non-root user")
                    logger.warning("Byte counts will be 0 without packet capture")
                else:
                    self.network_capture = NetworkCapture()
                    # Start in separate thread (scapy uses blocking sniff)
                    self._capture_thread = threading.Thread(
                        target=self.network_capture.start,
                        args=(self._handle_packet,),
                        daemon=True,
                        name="PacketCaptureThread"
                    )
                    self._capture_thread.start()
                    logger.info("Packet capture started successfully")
            except Exception as e:
                logger.error(f"Failed to start packet capture: {e}", exc_info=True)
                logger.warning("Continuing without packet capture - byte counts will be 0")
        elif self.enable_packet_capture and not SCAPY_AVAILABLE:
            logger.warning("Scapy not available - packet capture disabled")
            logger.warning("Byte counts will be 0 without packet capture")

        # Start main sampling loop
        await self._sampling_loop()

    async def stop(self) -> None:
        """Stop the daemon gracefully."""
        if not self.running:
            return

        logger.info("Stopping network monitoring daemon")
        self.running = False

        # Stop packet capture
        if self.network_capture:
            logger.info("Stopping packet capture")
            self.network_capture.stop()
            if self._capture_thread:
                self._capture_thread.join(timeout=5)
                if self._capture_thread.is_alive():
                    logger.warning("Packet capture thread did not stop gracefully")

        # Stop retention scheduler
        if self.retention_scheduler:
            await self.retention_scheduler.stop()

        logger.info(f"Daemon stopped. Collected {self.samples_collected} samples, {self.errors_count} errors, {self.packets_processed} packets")

    def _handle_packet(self, packet_info: PacketInfo) -> None:
        """
        Handle captured packet - update connection stats.

        Called from packet capture thread, so must be thread-safe.

        Args:
            packet_info: Information extracted from captured packet
        """
        try:
            # Use (dst_ip, dst_port) as connection key
            key = (packet_info.dst_ip, packet_info.dst_port)

            with self._stats_lock:
                stats = self.connection_stats[key]

                # Update byte and packet counts
                if packet_info.direction == "sent":
                    stats['bytes_sent'] += packet_info.packet_size
                    stats['packets_sent'] += 1
                else:
                    stats['bytes_received'] += packet_info.packet_size
                    stats['packets_received'] += 1

                # Track domain if available
                if packet_info.domain:
                    stats['domains'].add(packet_info.domain)

                self.packets_processed += 1

        except Exception as e:
            logger.debug(f"Error handling packet: {e}")

    async def _sampling_loop(self) -> None:
        """Main sampling loop - runs every N seconds."""
        logger.info("Starting sampling loop")

        while self.running:
            try:
                await self._sample_network()
                await asyncio.sleep(self.sampling_interval)
            except asyncio.CancelledError:
                logger.info("Sampling loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in sampling loop: {e}", exc_info=True)
                self.errors_count += 1
                await asyncio.sleep(self.sampling_interval)

    async def _sample_network(self) -> None:
        """
        Sample current network state.

        1. Get all network processes from lsof
        2. Map connections (IP:port) to processes
        3. Aggregate bytes from connection_stats for each process
        4. Store samples in database with REAL byte counts
        5. Track domains for browser processes
        """
        timestamp = datetime.now()

        try:
            # Get all processes with network connections
            processes = self.process_mapper.get_all_network_processes()

            if not processes:
                logger.debug("No network processes found in this sample")
                return

            # Build mapping: (dst_ip, dst_port) -> ProcessInfo
            connection_to_process: Dict[Tuple[str, int], ProcessInfo] = {}
            for proc in processes:
                if proc.remote_address and ':' in proc.remote_address:
                    try:
                        ip, port_str = proc.remote_address.rsplit(':', 1)
                        port = int(port_str)
                        key = (ip, port)
                        connection_to_process[key] = proc
                    except (ValueError, AttributeError):
                        continue

            # Aggregate bytes per process
            process_stats: Dict[Tuple[str, Optional[str]], Dict] = defaultdict(lambda: {
                'bytes_sent': 0,
                'bytes_received': 0,
                'packets_sent': 0,
                'packets_received': 0,
                'active_connections': 0,
                'domains': set()
            })

            # Take snapshot of connection_stats (thread-safe)
            with self._stats_lock:
                connection_stats_snapshot = dict(self.connection_stats)
                # Reset stats for next interval
                self.connection_stats.clear()

            # Map connection stats to processes
            for conn_key, stats in connection_stats_snapshot.items():
                dst_ip, dst_port = conn_key

                # Find which process owns this connection
                if conn_key in connection_to_process:
                    proc = connection_to_process[conn_key]
                    proc_key = (proc.name, proc.bundle_id)

                    # Aggregate stats for this process
                    process_stats[proc_key]['bytes_sent'] += stats['bytes_sent']
                    process_stats[proc_key]['bytes_received'] += stats['bytes_received']
                    process_stats[proc_key]['packets_sent'] += stats['packets_sent']
                    process_stats[proc_key]['packets_received'] += stats['packets_received']
                    process_stats[proc_key]['active_connections'] += 1
                    process_stats[proc_key]['domains'].update(stats['domains'])
                else:
                    logger.debug(f"Connection {dst_ip}:{dst_port} not mapped to any process")

            # Also add processes with connections but no captured packets yet
            seen_processes = {}
            for proc in processes:
                key = (proc.name, proc.bundle_id)
                if key not in seen_processes:
                    seen_processes[key] = proc
                    # Initialize in process_stats if not present
                    if key not in process_stats:
                        process_stats[key] = {
                            'bytes_sent': 0,
                            'bytes_received': 0,
                            'packets_sent': 0,
                            'packets_received': 0,
                            'active_connections': len([p for p in processes if p.name == proc.name]),
                            'domains': set()
                        }

            # Create samples for each process
            for proc_key, stats in process_stats.items():
                try:
                    proc_name, bundle_id = proc_key

                    # Get or create application
                    proc_info = seen_processes.get(proc_key)
                    if not proc_info:
                        # Create minimal ProcessInfo for stats-only entries
                        from src.process_mapper import ProcessInfo
                        proc_info = ProcessInfo(
                            pid=0,
                            name=proc_name,
                            bundle_id=bundle_id
                        )

                    app_id = await self._get_or_create_app(proc_info)
                    if not app_id:
                        continue

                    # Create network sample with REAL bytes
                    sample = NetworkSample(
                        timestamp=timestamp,
                        app_id=app_id,
                        bytes_sent=stats['bytes_sent'],
                        bytes_received=stats['bytes_received'],
                        packets_sent=stats['packets_sent'],
                        packets_received=stats['packets_received'],
                        active_connections=stats['active_connections']
                    )

                    await insert_network_sample(sample)
                    self.samples_collected += 1

                    # Track browser domains if any
                    if stats['domains'] and self._is_browser(proc_name):
                        await self._record_browser_domains(
                            app_id=app_id,
                            domains=stats['domains'],
                            timestamp=timestamp,
                            bytes_sent=stats['bytes_sent'],
                            bytes_received=stats['bytes_received']
                        )

                except Exception as e:
                    logger.error(f"Error processing process {proc_name}: {e}", exc_info=True)
                    self.errors_count += 1

            logger.debug(f"Sampled {len(process_stats)} unique processes, {len(processes)} total connections")

        except Exception as e:
            logger.error(f"Error sampling network: {e}", exc_info=True)
            self.errors_count += 1

    def _is_browser(self, process_name: str) -> bool:
        """
        Check if process is a web browser.

        Args:
            process_name: Name of the process

        Returns:
            True if process is a known browser
        """
        browsers = {
            'zen', 'chrome', 'firefox', 'safari', 'edge', 'brave',
            'opera', 'vivaldi', 'chromium', 'google chrome'
        }
        return process_name.lower() in browsers

    async def _record_browser_domains(
        self,
        app_id: int,
        domains: Set[str],
        timestamp: datetime,
        bytes_sent: int,
        bytes_received: int
    ) -> None:
        """
        Record browser domain samples from captured packets.

        Args:
            app_id: Application ID of browser
            domains: Set of domains accessed by browser
            timestamp: Timestamp of sample
            bytes_sent: Total bytes sent (distributed across domains)
            bytes_received: Total bytes received (distributed across domains)
        """
        try:
            # Distribute bytes evenly across domains (rough approximation)
            # In reality, would need per-domain tracking from packet capture
            num_domains = len(domains)
            bytes_per_domain_sent = bytes_sent // num_domains if num_domains > 0 else 0
            bytes_per_domain_recv = bytes_received // num_domains if num_domains > 0 else 0

            for domain in domains:
                try:
                    # Get or create domain
                    full_domain, parent_domain = get_domain_with_parent(domain)
                    domain_obj = await get_domain_by_name(full_domain)

                    if domain_obj:
                        domain_id = domain_obj.domain_id
                    else:
                        new_domain = Domain(
                            domain=full_domain,
                            parent_domain=parent_domain
                        )
                        domain_id = await insert_domain(new_domain)

                    # Create browser domain sample
                    sample = BrowserDomainSample(
                        timestamp=timestamp,
                        domain_id=domain_id,
                        app_id=app_id,
                        bytes_sent=bytes_per_domain_sent,
                        bytes_received=bytes_per_domain_recv
                    )

                    await insert_browser_domain_sample(sample)
                    logger.debug(f"Recorded browser domain: {full_domain}")

                except Exception as e:
                    logger.error(f"Error recording domain {domain}: {e}")

        except Exception as e:
            logger.error(f"Error recording browser domains: {e}", exc_info=True)

    async def _get_or_create_app(self, proc: ProcessInfo) -> Optional[int]:
        """
        Get or create application in database.

        Args:
            proc: ProcessInfo from process mapper

        Returns:
            Application ID
        """
        # Check cache first
        cache_key = f"{proc.name}:{proc.bundle_id}"
        if cache_key in self.app_id_cache:
            return self.app_id_cache[cache_key]

        # Try to get from database
        app = await get_application_by_name(proc.name, proc.bundle_id)

        if app:
            app_id = app.app_id
        else:
            # Create new application
            new_app = Application(
                process_name=proc.name,
                bundle_id=proc.bundle_id
            )
            app_id = await insert_application(new_app)

        # Cache the ID
        self.app_id_cache[cache_key] = app_id
        return app_id

    async def record_browser_domain(
        self,
        domain: str,
        browser: str,
        bytes_sent: int = 0,
        bytes_received: int = 0
    ) -> None:
        """
        Record browser domain usage (called by browser extension API).

        Args:
            domain: Domain name (e.g., netflix.com)
            browser: Browser name (e.g., zen, chrome)
            bytes_sent: Bytes sent (if available)
            bytes_received: Bytes received (if available)
        """
        try:
            # Normalize and get parent domain
            full_domain, parent_domain = get_domain_with_parent(domain)

            # Get or create domain
            domain_obj = await get_domain_by_name(full_domain)
            if domain_obj:
                domain_id = domain_obj.domain_id
            else:
                new_domain = Domain(
                    domain=full_domain,
                    parent_domain=parent_domain
                )
                domain_id = await insert_domain(new_domain)

            # Get browser app_id
            browser_app = await get_application_by_name(browser)
            if not browser_app:
                # Create browser application
                browser_app_obj = Application(
                    process_name=browser,
                    bundle_id=f"browser.{browser}"
                )
                app_id = await insert_application(browser_app_obj)
            else:
                app_id = browser_app.app_id

            # Create browser domain sample
            sample = BrowserDomainSample(
                domain_id=domain_id,
                app_id=app_id,
                bytes_sent=bytes_sent,
                bytes_received=bytes_received
            )

            await insert_browser_domain_sample(sample)
            logger.debug(f"Recorded browser domain: {full_domain} ({browser})")

        except Exception as e:
            logger.error(f"Error recording browser domain: {e}", exc_info=True)

    def get_status(self) -> dict:
        """
        Get daemon status information.

        Returns:
            Dictionary with status info
        """
        return {
            'running': self.running,
            'sampling_interval': self.sampling_interval,
            'samples_collected': self.samples_collected,
            'errors_count': self.errors_count,
            'packets_processed': self.packets_processed,
            'cached_apps': len(self.app_id_cache),
            'cached_domains': len(self.domain_id_cache),
            'retention_enabled': self.enable_retention,
            'packet_capture_enabled': self.enable_packet_capture,
            'packet_capture_active': self.network_capture is not None and self.network_capture.running
        }


# Global daemon instance
_daemon_instance: Optional[NetworkDaemon] = None


def get_daemon() -> Optional[NetworkDaemon]:
    """Get the global daemon instance."""
    return _daemon_instance


def set_daemon(daemon: NetworkDaemon) -> None:
    """Set the global daemon instance."""
    global _daemon_instance
    _daemon_instance = daemon


async def run_daemon(
    sampling_interval: int = 5,
    enable_retention: bool = True
) -> None:
    """
    Run the network monitoring daemon.

    Args:
        sampling_interval: Seconds between samples
        enable_retention: Enable automatic data retention/aggregation
    """
    daemon = NetworkDaemon(
        sampling_interval=sampling_interval,
        enable_retention=enable_retention
    )

    set_daemon(daemon)

    try:
        await daemon.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        await daemon.stop()
