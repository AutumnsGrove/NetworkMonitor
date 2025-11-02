"""
Network monitoring daemon.

Main daemon loop that samples network usage every 5 seconds,
uses macOS nettop for per-process tracking, and stores data in database.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Set

from src.process_mapper import ProcessMapper, ProcessInfo
from src.capture import NetTopMonitor
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

    Uses macOS nettop for per-process network monitoring.

    Responsibilities:
    1. Sample network usage every N seconds using nettop
    2. Store per-process network samples in database
    3. Track domains separately (from browser extension)
    4. Handle graceful shutdown

    Advantages of nettop approach:
    - No sudo required
    - Per-process attribution built-in
    - Simple, reliable native macOS tool
    - Direct byte counts without complex packet correlation
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
            enable_packet_capture: Enable network monitoring (using nettop)
        """
        self.sampling_interval = sampling_interval
        self.enable_retention = enable_retention
        self.enable_packet_capture = enable_packet_capture
        self.running = False
        self.process_mapper = ProcessMapper()
        self.retention_scheduler: Optional[RetentionScheduler] = None
        self.nettop_monitor: Optional[NetTopMonitor] = None

        # Track app_id mapping (cache for lookups)
        self.app_id_cache: Dict[str, int] = {}  # process_name -> app_id
        self.domain_id_cache: Dict[str, int] = {}  # domain -> domain_id

        # Statistics
        self.samples_collected = 0
        self.errors_count = 0

        logger.info(f"Initialized NetworkDaemon (interval: {sampling_interval}s, network_monitoring: {enable_packet_capture})")

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

        # Initialize nettop monitor if enabled
        if self.enable_packet_capture:
            self.nettop_monitor = NetTopMonitor()
            logger.info("Network monitoring using nettop (no sudo required)")
        else:
            logger.info("Network monitoring disabled")

        # Start main sampling loop
        await self._sampling_loop()

    async def stop(self) -> None:
        """Stop the daemon gracefully."""
        if not self.running:
            return

        logger.info("Stopping network monitoring daemon")
        self.running = False

        # Stop retention scheduler
        if self.retention_scheduler:
            await self.retention_scheduler.stop()

        logger.info(f"Daemon stopped. Collected {self.samples_collected} samples, {self.errors_count} errors")

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
        Sample current network state using nettop.

        Gets per-process byte counts from nettop and stores them in database.
        Each process gets its own network sample with REAL byte counts.
        """
        timestamp = datetime.now()

        try:
            if not self.nettop_monitor:
                logger.debug("Network monitoring disabled")
                return

            # Get current stats from nettop
            processes = await self.nettop_monitor.sample()

            if not processes:
                logger.debug("No network activity detected by nettop")
                return

            # Process each app
            for proc_data in processes:
                try:
                    # Get or create application
                    proc_name = proc_data['process_name']
                    app = await get_application_by_name(proc_name)

                    if not app:
                        new_app = Application(
                            process_name=proc_name,
                            bundle_id=f"process.{proc_name}"
                        )
                        app_id = await insert_application(new_app)
                    else:
                        app_id = app.app_id

                    # Create sample with REAL bytes from nettop
                    sample = NetworkSample(
                        timestamp=timestamp,
                        app_id=app_id,
                        bytes_sent=proc_data['bytes_out'],
                        bytes_received=proc_data['bytes_in'],
                        packets_sent=0,  # nettop doesn't provide packet counts
                        packets_received=0,
                        active_connections=1
                    )

                    await insert_network_sample(sample)
                    self.samples_collected += 1

                    if proc_data['bytes_in'] > 0 or proc_data['bytes_out'] > 0:
                        logger.info(f"{proc_name}: {proc_data['bytes_out']} sent, {proc_data['bytes_in']} recv")

                except Exception as e:
                    logger.error(f"Error processing {proc_data}: {e}")

            logger.debug(f"Sampled {len(processes)} processes from nettop")

        except Exception as e:
            logger.error(f"Error in nettop sampling: {e}", exc_info=True)
            self.errors_count += 1


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
            'cached_apps': len(self.app_id_cache),
            'cached_domains': len(self.domain_id_cache),
            'retention_enabled': self.enable_retention,
            'network_monitoring_enabled': self.enable_packet_capture,
            'nettop_active': self.nettop_monitor is not None
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
