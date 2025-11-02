# MenuBar Application Usage

## Overview

The Network Monitor MenuBar app provides quick access to network statistics and controls from your macOS menu bar. It displays real-time bandwidth usage, daily totals, and allows you to control the monitoring daemon without opening the dashboard.

## Starting the MenuBar App

### Method 1: Direct Python Execution

Run from project root:
```bash
python scripts/run_menubar.py
```

### Method 2: Using UV (Recommended)

```bash
uv run python scripts/run_menubar.py
```

### Method 3: From Source

```bash
python -m src.menubar
```

## Features

### Menu Items

The menubar provides the following options:

- **Current Usage** - Real-time bandwidth usage (updated every 30 seconds)
  - Shows current bytes/second in human-readable format
  - Example: "Current: 5.2 MB/s"

- **Today's Total** - Total data transferred since midnight
  - Cumulative bytes for the current day
  - Example: "Today: 1.8 GB"

- **Open Dashboard** - Opens the web dashboard in your default browser
  - Opens http://localhost:7500/dashboard/
  - Requires FastAPI server to be running

- **Refresh Stats** - Manually refresh statistics
  - Forces immediate update of stats
  - Shows notification with today's total

- **Start Daemon** - Start the network monitoring daemon
  - Sends API request to start daemon
  - Shows notification on success/failure
  - Menu item disabled when daemon is running

- **Stop Daemon** - Stop the network monitoring daemon
  - Sends API request to stop daemon
  - Shows notification on success/failure
  - Menu item disabled when daemon is stopped

- **View Logs** - Opens logs directory in Finder
  - Opens ~/.netmonitor/logs directory
  - Creates directory if it doesn't exist

- **Quit Network Monitor** - Exit the menubar application
  - Cleanly shuts down the menubar app
  - Does not affect daemon or server

### Dynamic Icons

The menubar icon changes based on current bandwidth usage:

| Icon | Usage Level | Threshold |
|------|-------------|-----------|
| 📶 | Low usage | < 1 MB/s |
| 📡 | Medium usage | 1-10 MB/s |
| 🚀 | High usage | > 10 MB/s |
| ⚠️ | Offline/Error | API unavailable |

### Notifications

The menubar app sends macOS notifications for the following events:

1. **High Usage Alert**
   - Triggered when bandwidth exceeds 50 MB/s
   - Includes current usage in message
   - Cooldown: 5 minutes between notifications
   - Prevents notification spam

2. **Stats Refreshed**
   - Confirms manual refresh
   - Shows today's total data usage

3. **Daemon Start/Stop**
   - Confirms daemon control actions
   - Shows error if action fails

## Configuration

### Notification Thresholds

Edit these values in `src/menubar.py`:

```python
# Line ~28
self.high_usage_threshold_mb = 50  # 50 MB/s default

# Line ~30
self.notification_cooldown_seconds = 300  # 5 minutes default
```

### Update Interval

The menubar updates stats every 30 seconds by default.

To change this, edit `src/menubar.py`:

```python
# Line ~52
self.timer = rumps.Timer(self.update_stats, 30)  # Change 30 to desired seconds
```

Recommended range: 10-60 seconds
- Lower values = more current stats, higher CPU usage
- Higher values = less frequent updates, lower CPU usage

## Requirements

### System Requirements

- macOS 10.10 (Yosemite) or later
- Python 3.10+
- Tk support (usually included with Python)

### Python Dependencies

- rumps >= 0.4.0
- requests >= 2.31.0

Install dependencies:
```bash
uv add rumps requests
```

Or with pip:
```bash
pip install rumps requests
```

### Running Services

The menubar app requires the FastAPI server to be running:

```bash
# In a separate terminal
python src/webserver.py
```

Or start the complete stack (when main.py is implemented):
```bash
python main.py
```

## Troubleshooting

### Issue: Menubar app doesn't appear

**Possible Causes:**
- rumps not installed
- macOS version too old
- Python doesn't have Tk support

**Solutions:**
```bash
# Verify rumps is installed
uv pip list | grep rumps

# Reinstall rumps
uv add rumps --reinstall

# Check macOS version
sw_vers
```

### Issue: Stats show "Offline"

**Possible Causes:**
- FastAPI server not running
- Server on wrong port
- Network connection issue

**Solutions:**
```bash
# Check if server is running
curl http://localhost:7500/api/stats

# Start server
python src/webserver.py

# Check server logs
tail -f ~/.netmonitor/logs/webserver.log
```

### Issue: Daemon controls don't work

**Possible Causes:**
- Daemon endpoints not implemented yet
- Server not responding
- Daemon already in desired state

**Solutions:**
- Verify API endpoints exist in webserver.py
- Check server logs for errors
- Manually control daemon until main.py orchestrator is complete

### Issue: Notifications not appearing

**Possible Causes:**
- Notification permissions not granted
- System notifications disabled
- Sound settings muted

**Solutions:**
1. Open System Preferences > Notifications
2. Find Python in app list
3. Enable "Allow Notifications"
4. Set alert style to "Alerts" or "Banners"

### Issue: High CPU usage

**Possible Causes:**
- Update interval too short
- Multiple instances running
- API calls timing out

**Solutions:**
```bash
# Increase update interval in menubar.py
# Line ~52: Change timer value from 30 to 60

# Check for multiple instances
ps aux | grep run_menubar.py

# Kill duplicate instances
pkill -f run_menubar.py
```

## Integration with Main App

The menubar app is designed to integrate with the complete Network Monitor stack:

```
main.py (orchestrator)
├── Network Daemon (packet capture)
├── FastAPI Server (API + Dashboard)
└── MenuBar App (system tray interface)
```

When `main.py` is implemented:
- All three components run in single process
- Daemon controls will be fully functional
- Start/stop affects the daemon thread
- Unified logging and error handling

## Privacy & Security

- **All data stays local** - No external API calls
- **No telemetry** - No usage tracking or analytics
- **Local API only** - Server bound to localhost:7500
- **No network access** - Menubar only queries local API

## Advanced Usage

### Running on Startup

To launch menubar app on login:

1. Open System Preferences > Users & Groups
2. Click "Login Items" tab
3. Click "+" button
4. Navigate to `scripts/run_menubar.py`
5. Add and enable

Or create a LaunchAgent (advanced):

```xml
<!-- ~/Library/LaunchAgents/com.netmonitor.menubar.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.netmonitor.menubar</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/path/to/NetworkMonitor/scripts/run_menubar.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
```

Load with:
```bash
launchctl load ~/Library/LaunchAgents/com.netmonitor.menubar.plist
```

### Custom Icons

To use custom .icns files instead of emoji:

1. Create or download .icns files (low.icns, medium.icns, high.icns)
2. Place in `assets/icons/` directory
3. Edit `src/menubar.py`:

```python
# Replace update_icon() method
def update_icon(self):
    """Update menu bar icon based on current bandwidth usage."""
    mb_per_sec = self.current_usage_bytes / (1024 * 1024)

    if mb_per_sec < 1:
        self.icon = "assets/icons/low.icns"
    elif mb_per_sec < 10:
        self.icon = "assets/icons/medium.icns"
    else:
        self.icon = "assets/icons/high.icns"
```

## API Endpoints Used

The menubar app calls these FastAPI endpoints:

- `GET /api/stats` - Fetch current and today's stats
- `GET /api/config/daemon/status` - Check daemon running state
- `POST /api/config/daemon/start` - Start daemon
- `POST /api/config/daemon/stop` - Stop daemon

See `docs/api_reference.md` for complete API documentation.

## Next Steps

- Implement Browser Extension (Phase 7)
- Add main.py orchestrator for unified control
- Create proper app icon set
- Package as standalone macOS app
- Add more configurable thresholds

## Feedback & Issues

The menubar app is in active development. Features planned:

- Configurable notification thresholds via UI
- More detailed stats in menu (top apps, top domains)
- Quick stats history (sparkline graphs)
- Dark mode support
- Custom keyboard shortcuts

---

*Last updated: 2025-11-01*
*Phase 6 - MenuBar Application*
