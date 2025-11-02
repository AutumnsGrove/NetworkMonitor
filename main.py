#!/usr/bin/env python3
"""
Network Monitor - Main Entry Point
Orchestrates daemon, webserver, and menubar in single process.
"""

import sys
import signal
import threading
import logging
import asyncio
import argparse
from pathlib import Path

# Setup logging first
from src.logging_config import setup_logging

# Import configuration
from src.config_manager import get_config, get_config_manager

# Import components
from src.daemon import NetworkDaemon, set_daemon
from src.menubar import NetworkMonitorMenuBar
from src.db_queries import init_database
from src.retention import RetentionScheduler
from src.utils import get_db_path, get_netmonitor_dir

# Global shutdown event
shutdown_event = threading.Event()
logger = None


class NetworkMonitorApp:
    """Main application orchestrator."""

    def __init__(self, debug=False, no_menubar=False, port=None):
        """Initialize the Network Monitor application."""
        global logger

        # Load configuration
        self.config = get_config()

        logger = setup_logging(debug=debug, log_to_console=True)
        logger.info("=== Network Monitor Starting ===")

        self.debug = debug
        self.no_menubar = no_menubar
        self.port = port if port is not None else self.config.server.port

        # Component references
        self.daemon = None
        self.webserver_thread = None
        self.menubar = None
        self.scheduler = None

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        shutdown_event.set()

        # Quit menubar if running
        if self.menubar:
            try:
                self.menubar.quit_application()
            except:
                pass

    def _start_webserver(self):
        """Start FastAPI webserver in background thread."""
        logger.info(f"Starting webserver on port {self.port}...")

        try:
            import uvicorn
            from src.webserver import app

            # Run uvicorn in this thread
            uvicorn.run(
                app,
                host="127.0.0.1",
                port=self.port,
                log_level="info" if not self.debug else "debug",
                access_log=False  # Reduce log noise
            )
        except Exception as e:
            logger.error(f"Webserver failed: {e}")
            shutdown_event.set()

    def _start_daemon(self):
        """Start network daemon in background thread with asyncio."""
        logger.info("Starting network daemon...")

        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Initialize daemon with config
            self.daemon = NetworkDaemon(
                sampling_interval=self.config.daemon.sampling_interval_seconds
            )

            # Register daemon globally for API access
            set_daemon(self.daemon)

            # Run daemon until shutdown
            async def run_daemon():
                try:
                    await self.daemon.start()
                    while not shutdown_event.is_set():
                        await asyncio.sleep(1)
                    await self.daemon.stop()
                except Exception as e:
                    logger.error(f"Daemon error: {e}")

            loop.run_until_complete(run_daemon())
            loop.close()
        except Exception as e:
            logger.error(f"Daemon thread failed: {e}")
            shutdown_event.set()

    def _start_scheduler(self):
        """Start data retention scheduler in background thread with asyncio."""
        logger.info("Starting data retention scheduler...")

        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Initialize scheduler with config
            self.scheduler = RetentionScheduler(
                aggregation_interval_seconds=self.config.retention.aggregation_interval_seconds,
                cleanup_interval_seconds=self.config.retention.cleanup_interval_seconds
            )

            # Run scheduler until shutdown
            async def run_scheduler():
                try:
                    await self.scheduler.start()
                    while not shutdown_event.is_set():
                        await asyncio.sleep(1)
                    await self.scheduler.stop()
                except Exception as e:
                    logger.error(f"Scheduler error: {e}")

            loop.run_until_complete(run_scheduler())
            loop.close()
        except Exception as e:
            logger.error(f"Scheduler thread failed: {e}")

    def initialize(self):
        """Initialize all components."""
        logger.info("Initializing Network Monitor...")

        # Create .netmonitor directory
        netmonitor_dir = get_netmonitor_dir()
        netmonitor_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Data directory: {netmonitor_dir}")

        # Initialize database
        db_path = get_db_path()
        logger.info(f"Database: {db_path}")

        try:
            init_database()
            logger.info("Database initialized")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            sys.exit(1)

    def start_background_components(self):
        """Start daemon, webserver, and scheduler in background threads."""

        # Start daemon thread
        daemon_thread = threading.Thread(
            target=self._start_daemon,
            daemon=True,
            name="DaemonThread"
        )
        daemon_thread.start()
        logger.info("Daemon thread started")

        # Start webserver thread
        self.webserver_thread = threading.Thread(
            target=self._start_webserver,
            daemon=True,
            name="WebserverThread"
        )
        self.webserver_thread.start()
        logger.info("Webserver thread started")

        # Start scheduler thread
        scheduler_thread = threading.Thread(
            target=self._start_scheduler,
            daemon=True,
            name="SchedulerThread"
        )
        scheduler_thread.start()
        logger.info("Scheduler thread started")

        # Wait a moment for components to initialize
        import time
        time.sleep(2)
        logger.info("All background components started")

    def run(self):
        """Run the application."""
        # Initialize
        self.initialize()

        # Start background components
        self.start_background_components()

        # Start menubar (blocks in main thread)
        if not self.no_menubar:
            logger.info("Starting menubar app (main thread)...")
            try:
                self.menubar = NetworkMonitorMenuBar()
                self.menubar.run()  # Blocks until quit
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
            except Exception as e:
                logger.error(f"Menubar failed: {e}")
            finally:
                shutdown_event.set()
        else:
            logger.info("MenuBar disabled, running in headless mode")
            logger.info("Press Ctrl+C to quit")

            # Wait for shutdown signal
            try:
                while not shutdown_event.is_set():
                    threading.Event().wait(1)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                shutdown_event.set()

        # Cleanup
        logger.info("Shutting down...")
        logger.info("=== Network Monitor Stopped ===")


def main():
    """Entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Network Monitor - Track application-level network usage"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--no-menubar",
        action="store_true",
        help="Run without menubar (headless mode)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Web server port (default: from config file)"
    )

    args = parser.parse_args()

    # Create and run application
    app = NetworkMonitorApp(
        debug=args.debug,
        no_menubar=args.no_menubar,
        port=args.port
    )
    app.run()


if __name__ == "__main__":
    main()
