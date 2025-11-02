# Network Monitor - Startup Guide

**Quick Start**: `sudo uv run python main.py`

---

## Prerequisites

1. **Python 3.10+** installed
2. **uv package manager** installed
3. **Dependencies synced**: Run `uv sync` if first time

---

## Starting the Application

### Method 1: Full Application (Recommended)

```bash
# Start all components (daemon + webserver + menubar)
sudo uv run python main.py
```

**What this does:**
- ✅ Starts FastAPI web server on localhost:7500
- ✅ Starts network monitoring daemon (5-second sampling)
- ✅ Starts data retention scheduler
- ✅ Launches macOS menubar app
- ✅ Initializes database at `~/.netmonitor/network_monitor.db`
- ✅ Creates logs at `~/.netmonitor/logs/`

**Why sudo?**
- Packet capture (scapy) requires root permissions to monitor network traffic
- The daemon maps network connections to applications via lsof

### Method 2: Headless Mode (No MenuBar)

```bash
# Run without menubar (for testing or remote environments)
sudo uv run python main.py --no-menubar
```

**Use this when:**
- Testing the daemon/webserver without GUI
- Running on a remote machine
- Debugging without menubar interference

### Method 3: Debug Mode

```bash
# Enable verbose debug logging
sudo uv run python main.py --debug
```

**Logs to:**
- Console (live output)
- File: `~/.netmonitor/logs/network_monitor.log`

---

## Accessing the Dashboard

Once started, open your browser to:

**Dashboard**: http://localhost:7500/dashboard/

**API Documentation**: http://localhost:7500/docs

**API Health Check**: http://localhost:7500/health

---

## MenuBar App

The menubar icon (📶) appears in your macOS menu bar when `main.py` is running.

**MenuBar Features:**
- Current bandwidth usage display
- Today's total data usage
- Quick access to dashboard (click "Open Dashboard")
- Start/stop daemon controls
- Auto-refresh every 30 seconds
- High usage notifications (>50 MB/s)

**Important**: The menubar app **cannot** be run standalone. It requires the webserver to be running via `main.py`.

---

## Browser Extension (Zen Browser)

The browser extension is located in `extension/` directory.

**Installation:**
1. Open Zen browser
2. Navigate to `about:debugging#/runtime/this-firefox`
3. Click "Load Temporary Add-on"
4. Select `extension/manifest.json`
5. Extension will start tracking active tabs and report to localhost:7500

**What it does:**
- Tracks your active browser tab domains
- Reports domain usage to the Network Monitor API
- Enables browser-specific domain analytics in the dashboard

---

## Stopping the Application

**Method 1: MenuBar**
- Click the menubar icon → "Quit Network Monitor"

**Method 2: Terminal**
- Press `Ctrl+C` in the terminal where `main.py` is running

**Method 3: Force Kill**
```bash
# Find the process
ps aux | grep "python main.py"

# Kill it
sudo kill -TERM <PID>
```

All components will shut down gracefully and save state.

---

## Troubleshooting

### Error: "Connection Refused" when clicking "Start Daemon"

**Cause**: The FastAPI web server isn't running.

**Solution**:
- Don't run `python src/menubar.py` directly
- Run `sudo uv run python main.py` instead
- The menubar app is launched automatically by `main.py`

### Error: "Failed to setup the notification center" (Info.plist)

**Cause**: Missing Info.plist file in virtual environment.

**Solution**:
```bash
/usr/libexec/PlistBuddy -c 'Add :CFBundleIdentifier string "com.networkmonitor.app"' /Users/mini/Documents/Projects/NetworkMonitor/.venv/bin/Info.plist
```

This is a **one-time setup** and persists across restarts.

### Dashboard shows "Offline" or "N/A"

**Possible causes:**
1. Daemon not running → Click "Start Daemon" in menubar
2. No network activity captured yet → Wait 30 seconds for first sample
3. Database not initialized → Check logs at `~/.netmonitor/logs/`

**Solution**:
- Check daemon status: http://localhost:7500/api/config/daemon/status
- View logs: `tail -f ~/.netmonitor/logs/network_monitor.log`
- Restart: `Ctrl+C` and run `sudo uv run python main.py` again

### Can't access dashboard (localhost:7500)

**Check webserver is running:**
```bash
curl http://localhost:7500/health
```

**If no response:**
- Webserver failed to start (check logs)
- Port 7500 already in use (change with `--port 7501`)

**Change port:**
```bash
sudo uv run python main.py --port 7501
```

### Daemon not capturing data

**Verify packet capture permissions:**
```bash
# Test scapy access
sudo python -c "from scapy.all import sniff; print('Scapy OK')"
```

**Check network interface:**
```bash
# List available interfaces
python -c "from src.capture import list_interfaces; print(list_interfaces())"
```

**Common issues:**
- Not running with `sudo` → Packet capture requires root
- VPN active → May interfere with packet capture
- Firewall blocking → Check macOS firewall settings

### High CPU/Memory usage

**Check current stats:**
```bash
# Monitor logs
tail -f ~/.netmonitor/logs/network_monitor.log

# Check database size
du -h ~/.netmonitor/network_monitor.db
```

**Solutions:**
- Increase sampling interval (default: 5 seconds)
- Reduce retention periods (default: 7 days raw, 90 days hourly)
- Run data cleanup: Visit dashboard → Configuration → "Clear old samples"

---

## Directory Structure

```
~/.netmonitor/
├── network_monitor.db       # SQLite database
├── config.json              # Configuration (created on first run)
└── logs/
    └── network_monitor.log  # Application logs (rotated at 10MB)
```

---

## Command-Line Options

```bash
sudo uv run python main.py [OPTIONS]

Options:
  --debug          Enable debug logging (verbose output)
  --no-menubar     Run without menubar app (headless mode)
  --port PORT      Web server port (default: 7500)
  -h, --help       Show help message
```

**Examples:**
```bash
# Debug mode with custom port
sudo uv run python main.py --debug --port 8000

# Headless mode (no menubar)
sudo uv run python main.py --no-menubar

# Production mode (default)
sudo uv run python main.py
```

---

## Auto-Start on Login (LaunchAgent)

**Coming soon**: LaunchAgent plist for automatic startup on macOS login.

For now, you must manually run `sudo uv run python main.py` after each boot.

---

## Next Steps

1. **Start the app**: `sudo uv run python main.py`
2. **Open dashboard**: http://localhost:7500/dashboard/
3. **Install extension**: Load `extension/` into Zen browser
4. **Monitor usage**: Let it run for a few hours to collect data
5. **Explore dashboard**: Check the 5 visualization pages

---

## Getting Help

- **View logs**: `tail -f ~/.netmonitor/logs/network_monitor.log`
- **API docs**: http://localhost:7500/docs
- **Health check**: http://localhost:7500/health
- **Check this guide**: `STARTUP.md`
- **Report issues**: Check `TODOS.md` for known issues

---

**Ready to start?**

```bash
sudo uv run python main.py
```

Then visit: http://localhost:7500/dashboard/
