# Network Monitor - Testing Guide

Quick guide to verify everything is working after fixes.

---

## 🔄 Step 1: Restart the Application

**Stop current instance:**
- Click menubar icon → "Quit Network Monitor"
- Or press `Ctrl+C` in terminal

**Start with fixes:**
```bash
sudo uv run python main.py
```

Wait 5-10 seconds for everything to initialize.

---

## ⚙️ Step 2: Configuration File

### Config File Location
All configuration is stored in **`config.yaml`** in the project root folder.

### View Current Configuration:
```bash
cat config.yaml
```

### Test Config API:
```bash
# Get all config values with sources (file/database/default)
curl http://localhost:7500/api/config/all
```

### Customize Settings
Edit `config.yaml` (in project folder) to change:
- **Sampling interval:** How often network is sampled (default: 1 second)
- **Port:** Web server port (default: 7500)
- **Retention policies:** How long to keep raw/aggregated data
- **MenuBar thresholds:** High usage alerts (default: 50 MB/s)
- **Refresh intervals:** Dashboard auto-refresh rates
- **Timeouts:** API and subprocess timeouts

**Example:**
```yaml
daemon:
  sampling_interval_seconds: 2  # Change from 1s to 2s

server:
  port: 8080  # Change from 7500 to 8080
```

**Restart required after config changes.**

---

## ✅ Step 3: Verify Daemon is Running

### Check via API:
```bash
curl http://localhost:7500/api/config/daemon/status
```

**Expected:** `{"running": true}`

### Check via MenuBar:
- Click the menubar icon
- "Start Daemon" should be disabled (grayed out)
- "Stop Daemon" should be enabled

### Check logs:
```bash
tail -20 ~/.netmonitor/logs/network_monitor.log
```

**Expected to see:**
```
INFO - Starting network monitoring daemon
INFO - Initialized NetworkDaemon (interval: 5s)
INFO - Starting network monitoring daemon
INFO - Starting sampling loop
```

**Should NOT see:**
- ❌ "signal only works in main thread"
- ❌ "NetworkDaemon.__init__() got an unexpected keyword argument"

---

## 📊 Step 4: Wait for Data Collection

The daemon samples every **1 second**. You need to:

1. **Browse the web** or use some apps (Slack, Discord, etc.)
2. **Wait 10-30 seconds** for data to accumulate (sampling every 1s now!)
3. **Refresh the dashboard** (or wait for auto-refresh)

---

## 🌐 Step 5: Test Browser Extension (Optional)

### Check Extension Status:
```bash
curl http://localhost:7500/api/browser/status
```

**Expected:**
```json
{
  "daemon_running": true,
  "api_version": "0.1.0",
  "accepting_reports": true
}
```

### Test Extension Manually:
```bash
# Send a test report
curl -X POST http://localhost:7500/api/browser/active-tab \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "netflix.com",
    "timestamp": "2025-11-02T12:00:00",
    "browser": "zen"
  }'
```

**Expected:** `{"status": "success", "domain_id": 1}`

### Check if Extension is Installed:
1. Open Zen browser
2. Go to `about:debugging#/runtime/this-firefox`
3. Look for "Network Monitor" in temporary extensions
4. Check browser console for errors: Right-click → Inspect → Console

---

## 📈 Step 6: Verify Dashboard Data

**Open dashboard:**
```bash
open http://localhost:7500/dashboard/
```

### What to check:

1. **Overview Page:**
   - Gauge shows current usage (may be "0 B/s" if idle)
   - Timeline graph appears (may be flat if no activity)
   - Top apps pie chart shows apps that used network
   - Top domains pie chart shows visited domains
   - Quick stats cards show totals

2. **Applications Page:**
   - Table shows applications that used network
   - Click an app → Timeline appears below

3. **Domains Page:**
   - Table shows domains visited
   - Parent domain rollup works (e.g., multiple Netflix subdomains)

4. **Historical Page:**
   - Heatmap may be empty if just started
   - Give it a few hours to build up data

5. **Configuration Page:**
   - "Daemon Status" shows "Running ✅"
   - System info displays correctly

---

## 🐛 Troubleshooting

### Dashboard shows "No data available"

**Cause:** Daemon not running or no network activity yet

**Fix:**
1. Check daemon status: `curl http://localhost:7500/api/config/daemon/status`
2. If not running, check logs: `tail ~/.netmonitor/logs/network_monitor.log`
3. Browse the web for 1-2 minutes
4. Refresh dashboard

### Daemon Status: "Running: false"

**Fix:**
1. Check logs for errors
2. Try clicking "Start Daemon" in menubar
3. Restart the app completely

### Dashboard Callback Errors

**Symptom:** Console shows KeyError about callbacks

**Fix:** These are warnings, not critical. The dashboard should still work. If persistent:
```bash
# Restart the app
sudo uv run python main.py
```

### Extension Not Reporting

**Check browser console:**
1. Right-click → Inspect → Console
2. Look for "Network Monitor" logs
3. Should see: "Network Monitor extension loaded"

**Common issues:**
- Extension not loaded in Zen browser
- API server not accessible (firewall?)
- Wrong API endpoint URL

### Database Queries Fail

**Symptom:** API returns errors about database

**Fix:**
```bash
# Check database exists
ls -lh ~/.netmonitor/network_monitor.db

# If corrupted, reset (WARNING: deletes all data)
rm ~/.netmonitor/network_monitor.db
# Restart app to recreate
```

---

## 🧪 Quick Test Sequence

**Full end-to-end test:**

```bash
# 1. Check API health
curl http://localhost:7500/health

# 2. Check daemon status
curl http://localhost:7500/api/config/daemon/status

# 3. Check current stats
curl http://localhost:7500/api/stats

# 4. Send test browser report
curl -X POST http://localhost:7500/api/browser/active-tab \
  -H "Content-Type: application/json" \
  -d '{"domain": "test.com", "timestamp": "2025-11-02T12:00:00", "browser": "zen"}'

# 5. Check applications
curl http://localhost:7500/api/applications?limit=5

# 6. Check domains
curl http://localhost:7500/api/domains?limit=5

# 7. Open dashboard
open http://localhost:7500/dashboard/
```

**All commands should return valid JSON (no errors).**

---

## 📝 Logs Locations

**Application logs:**
```
~/.netmonitor/logs/network_monitor.log
```

**LaunchAgent logs (if installed):**
```
~/.netmonitor/logs/launchagent.log
~/.netmonitor/logs/launchagent_error.log
```

**Database:**
```
~/.netmonitor/network_monitor.db
```

**View live logs:**
```bash
tail -f ~/.netmonitor/logs/network_monitor.log
```

---

## ✅ Success Criteria

Everything is working if:

- ✅ Daemon status shows "running: true"
- ✅ Menubar shows current usage (even if 0 B/s)
- ✅ Logs show "Starting sampling loop"
- ✅ Dashboard displays without errors
- ✅ After browsing, data appears in dashboard
- ✅ API endpoints return valid data

---

## 🔍 Data Collection Timeline

**Immediate (0-10 seconds):**
- Daemon starts
- Menubar shows status
- API responds

**After 30 seconds:**
- First samples collected
- Database has entries
- Stats API returns data

**After 2-5 minutes:**
- Timeline graph has visible data
- Top apps/domains appear
- Pie charts populate

**After 1 hour:**
- Hourly aggregates created
- Historical page has data
- Heatmap begins to form

---

**Need help?** Check logs first, then see `STARTUP.md` troubleshooting section.
