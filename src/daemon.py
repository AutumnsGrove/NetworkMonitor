"""
Network monitoring daemon.

Main daemon loop that samples network usage every 5 seconds,
maps connections to processes, and stores data in database.
"""
import asyncio
import logging
import signal
from datetime import datetime
from typing import Optional, Dict, Set
from collections import defaultdict

from src.process_mapper import ProcessMapper, ProcessInfo
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
        enable_retention: bool = True
    ):
        """
        Initialize network daemon.

        Args:
            sampling_interval: Seconds between samples (default 5)
            enable_retention: Enable automatic data retention/aggregation
        """
        self.sampling_interval = sampling_interval
        self.enable_retention = enable_retention
        self.running = False
        self.process_mapper = ProcessMapper()
        self.retention_scheduler: Optional[RetentionScheduler] = None

        # Track app_id mapping (cache for lookups)
        self.app_id_cache: Dict[str, int] = {}  # process_name -> app_id
        self.domain_id_cache: Dict[str, int] = {}  # domain -> domain_id

        # Active connections tracking
        self.active_connections: Dict[str, Set[int]] = defaultdict(set)

        # Statistics
        self.samples_collected = 0
        self.errors_count = 0

        logger.info(f"Initialized NetworkDaemon (interval: {sampling_interval}s)")

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
        Sample current network state.

        1. Get all network processes from lsof
        2. Calculate network usage (would need baseline comparison)
        3. Store samples in database
        """
        timestamp = datetime.now()

        try:
            # Get all processes with network connections
            processes = self.process_mapper.get_all_network_processes()

            if not processes:
                logger.debug("No network processes found in this sample")
                return

            # Track which apps are active this sample
            active_apps = set()

            # Process each unique process
            seen_processes = {}
            for proc in processes:
                key = (proc.name, proc.bundle_id)
                if key not in seen_processes:
                    seen_processes[key] = proc

            # For each unique process, create/update application and sample
            for key, proc in seen_processes.items():
                try:
                    # Get or create application
                    app_id = await self._get_or_create_app(proc)
                    if not app_id:
                        continue

                    active_apps.add(app_id)

                    # Create network sample
                    # Note: Without baseline, we can't calculate actual bytes
                    # This is a limitation of lsof-based approach
                    # For real implementation with scapy, we'd track actual packet counts
                    sample = NetworkSample(
                        timestamp=timestamp,
                        app_id=app_id,
                        bytes_sent=0,  # Would be calculated from packet capture
                        bytes_received=0,  # Would be calculated from packet capture
                        packets_sent=0,
                        packets_received=0,
                        active_connections=len([p for p in processes if p.name == proc.name])
                    )

                    await insert_network_sample(sample)
                    self.samples_collected += 1

                except Exception as e:
                    logger.error(f"Error processing process {proc.name}: {e}", exc_info=True)
                    self.errors_count += 1

            logger.debug(f"Sampled {len(seen_processes)} unique processes, {len(processes)} total connections")

        except Exception as e:
            logger.error(f"Error sampling network: {e}", exc_info=True)
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
            'retention_enabled': self.enable_retention
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
