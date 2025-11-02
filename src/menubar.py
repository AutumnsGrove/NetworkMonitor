"""macOS MenuBar application for Network Monitor."""

import rumps
import webbrowser
import requests
from datetime import datetime
from typing import Optional

from src.utils import format_bytes


class NetworkMonitorMenuBar(rumps.App):
    """macOS MenuBar application for Network Monitor."""

    def __init__(self):
        super(NetworkMonitorMenuBar, self).__init__(
            "Network Monitor",
            icon=None,  # Will set dynamic icon
            quit_button=None,  # Custom quit handler
        )

        # State
        self.daemon_running = False
        self.current_usage_bytes = 0
        self.today_total_bytes = 0

        # High usage notification settings
        self.high_usage_threshold_mb = 50  # 50 MB/s
        self.last_notification_time = None
        self.notification_cooldown_seconds = 300  # 5 minutes

        # Build menu
        self.menu = [
            rumps.MenuItem("Current Usage: Loading...", callback=None),
            rumps.MenuItem("Today's Total: Loading...", callback=None),
            rumps.separator,
            rumps.MenuItem("Open Dashboard", callback=self.open_dashboard),
            rumps.MenuItem("Refresh Stats", callback=self.refresh_stats),
            rumps.separator,
            rumps.MenuItem("Start Daemon", callback=self.start_daemon),
            rumps.MenuItem("Stop Daemon", callback=self.stop_daemon),
            rumps.separator,
            rumps.MenuItem("View Logs", callback=self.view_logs),
            rumps.separator,
            rumps.MenuItem("Quit Network Monitor", callback=self.quit_app),
        ]

        # Start background timer for auto-refresh
        self.timer = rumps.Timer(self.update_stats, 30)  # Every 30 seconds
        self.timer.start()

        # Initial update
        self.update_stats(None)

    def update_stats(self, sender):
        """Update menu bar stats from API."""
        try:
            # Fetch stats from API
            response = requests.get("http://localhost:7500/api/stats", timeout=3)
            data = response.json()

            # Update state
            self.today_total_bytes = data.get("today", {}).get("total_bytes", 0)
            self.current_usage_bytes = data.get("current", {}).get("bytes_per_second", 0)

            # Update menu items
            self.menu["Current Usage: Loading..."].title = f"Current: {format_bytes(self.current_usage_bytes)}/s"
            self.menu["Today's Total: Loading..."].title = f"Today: {format_bytes(self.today_total_bytes)}"

            # Update icon based on current usage
            self.update_icon()

            # Check daemon status
            self.check_daemon_status()

            # Check for high usage
            mb_per_sec = self.current_usage_bytes / (1024 * 1024)
            if mb_per_sec > self.high_usage_threshold_mb:
                self.notify_high_usage(mb_per_sec)

        except Exception as e:
            self.menu["Current Usage: Loading..."].title = "Current: Offline"
            self.menu["Today's Total: Loading..."].title = "Today: N/A"
            self.title = "⚠️"  # Warning icon

    def update_icon(self):
        """Update menu bar icon based on current bandwidth usage."""
        # Convert bytes/s to MB/s for thresholds
        mb_per_sec = self.current_usage_bytes / (1024 * 1024)

        if mb_per_sec < 1:
            self.title = "📶"  # Low usage (green)
        elif mb_per_sec < 10:
            self.title = "📡"  # Medium usage (yellow)
        else:
            self.title = "🚀"  # High usage (red)

    def check_daemon_status(self):
        """Check if daemon is running."""
        try:
            response = requests.get("http://localhost:7500/api/config/daemon/status", timeout=3)
            data = response.json()
            self.daemon_running = data.get("running", False)

            # Update Start/Stop menu items
            if self.daemon_running:
                self.menu["Start Daemon"].set_callback(None)  # Disable
                self.menu["Stop Daemon"].set_callback(self.stop_daemon)  # Enable
            else:
                self.menu["Start Daemon"].set_callback(self.start_daemon)  # Enable
                self.menu["Stop Daemon"].set_callback(None)  # Disable
        except:
            pass  # API offline

    def notify_high_usage(self, mb_per_sec: float):
        """Send notification for high bandwidth usage."""
        now = datetime.now()

        # Check cooldown
        if self.last_notification_time:
            elapsed = (now - self.last_notification_time).total_seconds()
            if elapsed < self.notification_cooldown_seconds:
                return  # Skip notification (in cooldown)

        # Send notification
        rumps.notification(
            title="Network Monitor",
            subtitle="High Bandwidth Usage",
            message=f"Current: {mb_per_sec:.1f} MB/s",
            sound=True,
        )

        self.last_notification_time = now

    def open_dashboard(self, sender):
        """Open web dashboard in default browser."""
        webbrowser.open("http://localhost:7500/dashboard/")

    def refresh_stats(self, sender):
        """Manually refresh statistics."""
        self.update_stats(None)
        rumps.notification(
            title="Network Monitor",
            subtitle="Stats Refreshed",
            message=f"Today's total: {format_bytes(self.today_total_bytes)}",
        )

    def start_daemon(self, sender):
        """Start the network monitoring daemon."""
        try:
            response = requests.post("http://localhost:7500/api/config/daemon/start", timeout=3)
            if response.status_code == 200:
                rumps.notification(
                    title="Network Monitor",
                    subtitle="Daemon Started",
                    message="Network monitoring is now active",
                )
                self.update_stats(None)  # Refresh status
            else:
                rumps.notification(
                    title="Network Monitor",
                    subtitle="Daemon Start Failed",
                    message="Could not start daemon - check logs",
                )
        except Exception as e:
            rumps.notification(
                title="Network Monitor",
                subtitle="Daemon Start Error",
                message="Server not responding - ensure FastAPI is running",
            )

    def stop_daemon(self, sender):
        """Stop the network monitoring daemon."""
        try:
            response = requests.post("http://localhost:7500/api/config/daemon/stop", timeout=3)
            if response.status_code == 200:
                rumps.notification(
                    title="Network Monitor",
                    subtitle="Daemon Stopped",
                    message="Network monitoring has been stopped",
                )
                self.update_stats(None)  # Refresh status
            else:
                rumps.notification(
                    title="Network Monitor",
                    subtitle="Daemon Stop Failed",
                    message="Could not stop daemon - check logs",
                )
        except Exception as e:
            rumps.notification(
                title="Network Monitor",
                subtitle="Daemon Stop Error",
                message="Server not responding - ensure FastAPI is running",
            )

    def view_logs(self, sender):
        """Open logs directory in Finder."""
        import subprocess
        import os
        log_dir = os.path.expanduser("~/.netmonitor/logs")
        # Create logs directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        subprocess.run(["open", log_dir])

    def quit_app(self, sender):
        """Quit the menubar application."""
        rumps.quit_application()


def run_menubar():
    """Entry point for menubar application."""
    app = NetworkMonitorMenuBar()
    app.run()


if __name__ == "__main__":
    run_menubar()
