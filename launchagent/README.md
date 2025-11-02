# Network Monitor - LaunchAgent Auto-Start

This directory contains the LaunchAgent configuration for automatically starting Network Monitor on macOS login.

---

## Quick Start

### Install LaunchAgent (Auto-Start on Login)

```bash
cd launchagent
./install.sh
```

This will:
1. ✅ Install the LaunchAgent to `~/Library/LaunchAgents/`
2. ✅ Configure passwordless sudo for the Network Monitor
3. ✅ Start the Network Monitor immediately
4. ✅ Enable auto-start on login

**After installation**, the Network Monitor will:
- Start automatically when you log in
- Run in the background continuously
- Be accessible at http://localhost:7500/dashboard/
- Display a menubar icon for quick access

### Uninstall LaunchAgent

```bash
cd launchagent
./uninstall.sh
```

This will:
1. Stop the running Network Monitor
2. Remove the LaunchAgent configuration
3. Remove sudo permissions
4. Disable auto-start on login

**After uninstallation**, you can still run the app manually:
```bash
sudo uv run python main.py
```

---

## How It Works

### LaunchAgent Configuration

The LaunchAgent (`com.networkmonitor.daemon.plist`) is installed to:
```
~/Library/LaunchAgents/com.networkmonitor.daemon.plist
```

It configures macOS to:
- Run Network Monitor automatically on login (`RunAtLoad`)
- Restart if it crashes (`KeepAlive`)
- Log output to `~/.netmonitor/logs/launchagent.log`
- Execute with proper PATH and environment

### Sudo Permissions

Network Monitor requires `sudo` for packet capture. The install script creates a sudoers entry:
```
/etc/sudoers.d/network-monitor
```

This allows the Network Monitor to run with elevated privileges **without** password prompts.

**Security Note:** The sudo permission is restricted to:
- Only the specific user who installed it
- Only the exact command: `uv run python main.py` in the project directory
- No other sudo commands are affected

### Logs

**LaunchAgent logs:**
- Standard output: `~/.netmonitor/logs/launchagent.log`
- Standard error: `~/.netmonitor/logs/launchagent_error.log`

**Application logs:**
- Main log: `~/.netmonitor/logs/network_monitor.log`

View logs in real-time:
```bash
# LaunchAgent logs
tail -f ~/.netmonitor/logs/launchagent.log

# Application logs
tail -f ~/.netmonitor/logs/network_monitor.log
```

---

## Verification

### Check if LaunchAgent is Running

```bash
launchctl list | grep com.networkmonitor.daemon
```

**Expected output:**
```
12345  0  com.networkmonitor.daemon
```
(The first number is the process ID)

### Check if Network Monitor is Accessible

```bash
curl http://localhost:7500/health
```

**Expected output:**
```json
{"status": "healthy", "version": "0.1.0"}
```

### Check LaunchAgent Status

```bash
launchctl print gui/$(id -u)/com.networkmonitor.daemon
```

This shows detailed LaunchAgent status and configuration.

---

## Manual Control

### Start LaunchAgent

```bash
launchctl load ~/Library/LaunchAgents/com.networkmonitor.daemon.plist
```

### Stop LaunchAgent

```bash
launchctl unload ~/Library/LaunchAgents/com.networkmonitor.daemon.plist
```

### Restart LaunchAgent

```bash
launchctl unload ~/Library/LaunchAgents/com.networkmonitor.daemon.plist
launchctl load ~/Library/LaunchAgents/com.networkmonitor.daemon.plist
```

---

## Troubleshooting

### LaunchAgent won't start

**Check logs:**
```bash
cat ~/.netmonitor/logs/launchagent_error.log
```

**Common issues:**
1. **UV not found** - Ensure UV is installed and in PATH
2. **Sudo permission denied** - Re-run `./install.sh` to configure sudo
3. **Port 7500 in use** - Another app is using the port

### Network Monitor crashes on startup

**Check application logs:**
```bash
cat ~/.netmonitor/logs/network_monitor.log
```

**Common issues:**
1. **Database corruption** - Delete `~/.netmonitor/network_monitor.db` to reset
2. **Permission errors** - Ensure sudo is configured correctly
3. **Missing dependencies** - Run `uv sync` in the project directory

### Sudo password still prompted

The sudoers file may not be configured correctly:

**Fix:**
```bash
cd launchagent
./uninstall.sh
./install.sh
```

This will recreate the sudoers configuration.

### LaunchAgent runs but menubar doesn't appear

The menubar app is part of the main process and should appear automatically.

**Check if the process is running:**
```bash
ps aux | grep "python main.py"
```

**If running but no menubar:**
- Try running manually to see errors: `sudo uv run python main.py`
- Check logs for rumps errors

---

## Uninstallation

To completely remove Network Monitor auto-start:

1. **Uninstall LaunchAgent:**
   ```bash
   cd launchagent
   ./uninstall.sh
   ```

2. **Optional: Remove all data:**
   ```bash
   rm -rf ~/.netmonitor/
   ```

3. **Optional: Uninstall UV tool:**
   ```bash
   uv tool uninstall network-monitor
   ```

---

## Alternative: Manual Startup

If you prefer not to use the LaunchAgent and want to start manually:

```bash
sudo uv run python main.py
```

Or install as a UV tool (see below):
```bash
uv tool install .
sudo network-monitor
```

---

## UV Tool Installation (Alternative)

Instead of using the LaunchAgent, you can install Network Monitor as a UV tool:

```bash
# Install as UV tool
uv tool install .

# Run from anywhere
sudo network-monitor

# With options
sudo network-monitor --debug
sudo network-monitor --port 8000
```

**Note:** The UV tool still requires `sudo` for packet capture.

**To uninstall the UV tool:**
```bash
uv tool uninstall network-monitor
```

---

## Security Considerations

### Sudo Access

The LaunchAgent requires sudo to:
- Capture network packets with scapy
- Map network connections to processes with lsof

**Restricted permissions:**
- Only your user account can run the command
- Only the specific `uv run python main.py` command is allowed
- No other sudo commands are affected

### Data Privacy

All data stays local:
- Database: `~/.netmonitor/network_monitor.db`
- Logs: `~/.netmonitor/logs/`
- Web server: `127.0.0.1:7500` (localhost only)
- No external API calls or telemetry

---

## Files

```
launchagent/
├── README.md                          # This file
├── com.networkmonitor.daemon.plist    # LaunchAgent configuration
├── install.sh                         # Installation script
└── uninstall.sh                       # Uninstallation script
```

**LaunchAgent location after installation:**
```
~/Library/LaunchAgents/com.networkmonitor.daemon.plist
```

**Sudoers file location after installation:**
```
/etc/sudoers.d/network-monitor
```

---

## Support

**View logs:**
```bash
tail -f ~/.netmonitor/logs/network_monitor.log
```

**Check daemon status:**
```bash
launchctl list | grep com.networkmonitor.daemon
```

**Check web server:**
```bash
curl http://localhost:7500/health
```

**Full troubleshooting guide:** See `../STARTUP.md`

---

**Quick Reference:**

```bash
# Install auto-start
cd launchagent && ./install.sh

# Uninstall auto-start
cd launchagent && ./uninstall.sh

# Check status
launchctl list | grep com.networkmonitor.daemon

# View logs
tail -f ~/.netmonitor/logs/network_monitor.log

# Access dashboard
open http://localhost:7500/dashboard/
```
