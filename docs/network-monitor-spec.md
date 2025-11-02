# Network Monitor - Project Specification

## Project Overview

A lightweight, privacy-focused network monitoring tool for macOS that tracks application-level network usage with enhanced domain-level tracking for web browsers. The system provides a rich web-based dashboard for visualizing network consumption patterns over time.

**Primary Goal:** Understand where network bandwidth is being consumed by tracking per-application usage and identifying high-traffic domains.

---

## System Architecture

### Components

1. **Background Daemon** - Captures network activity continuously
2. **Web Dashboard** - FastAPI + Plotly/Dash visualization interface
3. **SQLite Database** - Local persistent storage
4. **MenuBar App** - macOS menubar icon for quick status/controls
5. **Browser Extension** - Zen browser integration for domain tracking

### Unified vs. Separated Process
**Preferred:** Single unified Python process that handles daemon, web server, and menubar icon.
**Acceptable:** Two-process architecture if needed (daemon + web server).

---

## Technical Stack

### Core Technologies
- **Language:** Python 3.10+
- **Web Framework:** FastAPI
- **Visualization:** Plotly/Dash
- **Database:** SQLite
- **MenuBar:** rumps (or similar macOS menubar library)
- **Network Capture:** pcap/scapy (packet sniffing) OR lsof + DNS cache inspection
- **Auto-Start:** macOS LaunchAgent

### Browser Extension
- **Target:** Zen Browser (Firefox-based)
- **Technology:** WebExtensions API (JavaScript)
- **Function:** Report active tab domain to local API endpoint

---

## Functional Requirements

### 1. Network Capture & Monitoring

#### Application-Level Tracking
- Monitor all applications' network usage
- Track bytes sent/received per application
- Identify process names and PIDs
- Sample every **5 seconds** (configurable)

#### Domain-Level Tracking (Browser-Specific)
- For Zen browser: Track which domains consume data
- Roll up subdomains to parent domain (e.g., `api.netflix.com` → `netflix.com`)
- Correlate browser extension data with packet capture
- Keep domain names general (no full URLs with paths/parameters)

#### Capture Methods (Choose Best Fit)
**Option A: Packet Sniffing**
- Use pcap/scapy for deep packet inspection
- Requires sudo/root permissions
- Can decode DNS queries and HTTP/HTTPS SNI headers
- More accurate, higher overhead

**Option B: lsof + DNS Cache**
- Periodic lsof sampling for process connections
- Inspect DNS cache for domain mapping
- Lighter weight, less accurate
- No special permissions needed

**Recommendation:** Start with Option A (packet sniffing) since user is comfortable with local-only access.

### 2. Data Storage & Management

#### Database Schema
**SQLite Database Location:** `~/.netmonitor/network_monitor.db`

**Core Tables:**
- `network_samples` - Raw 5-second samples
- `hourly_aggregates` - Hourly rollups
- `daily_aggregates` - Daily summaries
- `applications` - Application metadata
- `domains` - Domain tracking for browsers
- `config` - Runtime configuration

**Data Retention Policy:**
- Keep raw samples for **7 days**
- Keep hourly aggregates for **30-90 days** (configurable)
- Automatic migration: Raw → Hourly after 7 days
- Prune old data automatically on startup/scheduled task

#### SQL Abstraction Layer
Create dedicated file: `db_queries.py`
- All SQL operations abstracted into functions
- No raw SQL in main application code
- Clean, testable, maintainable query interface

#### Database Security
- File permissions: 600 (owner read/write only)
- Database encryption not required (local-only access)
- No sensitive data exposure (domains kept general)

### 3. Web Dashboard

#### Server Configuration
- **Framework:** FastAPI with async support
- **Port:** 7000-7999 range (configurable, default: 7500)
- **Binding:** 127.0.0.1 (localhost only)
- **Authentication:** None (trust local machine access)
- **Always Running:** Web server runs continuously alongside daemon

#### Dashboard Features

**Page 1: Overview Dashboard**
- Real-time current usage gauge (live updates)
- Timeline graph: Network usage over time (last 24h, 7d, 30d views)
- Pie chart: Application breakdown (top 10 apps)
- Top domains table (for browsers)
- Quick stats: Total data today, this week, this month

**Page 2: Application Details**
- Sortable table of all applications
- Per-app timeline graphs
- Data sent/received breakdown
- Process details

**Page 3: Domain Analysis**
- Browser-specific domain breakdown
- Top domains by data consumption
- Domain timeline tracking
- Subdomain rollup visualization

**Page 4: Historical Analysis**
- Hourly heatmap (day of week × hour of day)
- Weekly trends
- Monthly comparisons
- Customizable date range selection

**Page 5: Configuration**
- Adjust sampling interval
- Set data retention policies
- Configure log levels
- View system status

#### Visualization Types
- **Timeline graphs:** Line charts with zoomable time ranges
- **Pie charts:** Application/domain breakdown
- **Gauges:** Real-time current bandwidth usage
- **Heatmaps:** Usage patterns by hour/day
- **Tables:** Sortable, filterable data tables with export options

### 4. MenuBar Application

#### Features
- **Icon:** Simple network activity indicator
- **Dropdown Menu:**
  - Current data usage (today)
  - Quick stats
  - "Open Dashboard" → Opens browser to 127.0.0.1:7500
  - "Pause/Resume Monitoring"
  - "View Logs"
  - "Quit"

#### Status Indication
- Icon changes based on current bandwidth usage (idle, low, medium, high)
- Optional notification for high usage events (configurable threshold)

### 5. Browser Extension (Zen Browser)

#### Functionality
- Track active tab URL domain
- Report to local API endpoint every 5 seconds (or on tab change)
- Lightweight, minimal permissions
- Simple POST to `http://127.0.0.1:7500/api/browser/active-tab`

#### API Payload
```json
{
  "domain": "netflix.com",
  "timestamp": 1699123456,
  "browser": "zen"
}
```

#### Extension Scope
- Only reports domain (not full URL)
- Only tracks active tab (not all tabs)
- No data storage in extension
- Privacy-first design

---

## Configuration Management

### config.json Location
`~/.netmonitor/config.json`

### Configuration Options
```json
{
  "sampling_interval_seconds": 5,
  "web_server_port": 7500,
  "log_level": "INFO",
  "data_retention_days_raw": 7,
  "data_retention_days_hourly": 90,
  "capture_method": "packet_sniffing",
  "domain_rollup": true,
  "high_usage_threshold_gb": 10,
  "enable_notifications": false
}
```

### Easy Access
- Config file clearly documented
- Editable via text editor OR web dashboard
- Changes take effect on restart (or live reload if possible)

---

## Logging & Debugging

### Log Configuration
- **Location:** `~/.netmonitor/logs/`
- **Log Levels:** DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Files:**
  - `daemon.log` - Background monitoring logs
  - `webserver.log` - FastAPI access/error logs
  - `extension.log` - Browser extension communication logs

### Log Rotation
- Max file size: 10MB
- Keep last 5 rotated files
- Compress old logs (gzip)

### Debug Mode
- Enable verbose logging via config.json
- Packet-level inspection logs (if using packet sniffing)
- SQL query logging

---

## Auto-Start & Lifecycle Management

### macOS LaunchAgent
- Create `~/Library/LaunchAgents/com.networkmonitor.daemon.plist`
- Auto-start on user login
- Restart on crash
- Run in background (no terminal window)

### Graceful Shutdown
- Handle SIGTERM/SIGINT properly
- Flush pending database writes
- Clean up network capture handles
- Save current state

### Updates & Maintenance
- Automatic database migrations on version updates
- Schema version tracking in database
- Backwards-compatible data retention

---

## Directory Structure

```
~/.netmonitor/
├── config.json              # User configuration
├── network_monitor.db       # SQLite database
├── logs/                    # Log files
│   ├── daemon.log
│   ├── webserver.log
│   └── extension.log
└── tmp/                     # Temporary files, cache
```

---

## Development Roadmap

### Phase 1: Core Daemon
- [ ] Set up project structure
- [ ] Implement packet capture OR lsof monitoring
- [ ] SQLite database setup with schema
- [ ] SQL abstraction layer (db_queries.py)
- [ ] Data collection loop (5-second sampling)
- [ ] Data retention & aggregation logic

### Phase 2: Web Dashboard
- [ ] FastAPI server setup
- [ ] Basic REST API endpoints
- [ ] Plotly/Dash integration
- [ ] Overview dashboard (timeline, pie chart, stats)
- [ ] Application details page
- [ ] Domain analysis page
- [ ] Historical analysis page
- [ ] Configuration page

### Phase 3: MenuBar App
- [ ] rumps menubar integration
- [ ] Status icon and menu
- [ ] Quick stats display
- [ ] Open dashboard functionality

### Phase 4: Browser Extension
- [ ] WebExtension manifest for Zen
- [ ] Active tab tracking
- [ ] API communication to local server
- [ ] Extension packaging and installation

### Phase 5: Auto-Start & Polish
- [ ] LaunchAgent setup
- [ ] Logging configuration
- [ ] Error handling and recovery
- [ ] Documentation and README
- [ ] Testing across various network conditions

### Phase 6: Enhancements (Future)
- [ ] Export data (CSV, JSON)
- [ ] Set usage alerts/budgets
- [ ] Compare time periods
- [ ] Machine learning for anomaly detection
- [ ] Support for other browsers (Chrome, Safari)

---

## Privacy & Security Considerations

### Local-Only Design
- All data stays on local machine
- No external API calls
- No telemetry or analytics
- No cloud sync

### Data Minimization
- Domain names kept general (no full URLs)
- No payload inspection (only headers/DNS)
- No storage of sensitive request parameters
- User can purge data at any time

### Access Control
- Web UI bound to localhost only
- Database file permissions restricted
- No authentication (trusted local access)
- Extension only communicates with localhost

---

## Performance Requirements

### Resource Usage Targets
- **CPU:** < 5% average
- **Memory:** < 100MB resident
- **Disk I/O:** Minimal (batch writes every 30s)
- **Network Overhead:** Negligible (monitoring only)

### Scalability
- Handle 100+ active connections simultaneously
- Process 1000+ samples per minute
- Database size growth: ~5-10MB per day
- Query response time: < 500ms for dashboard loads

---

## Testing Strategy

### Unit Tests
- SQL abstraction layer
- Data aggregation functions
- Domain rollup logic
- Configuration parsing

### Integration Tests
- End-to-end capture → storage → visualization
- Browser extension → API → database flow
- LaunchAgent startup/shutdown

### Manual Testing
- Various network conditions (idle, heavy download, streaming)
- Long-running stability (24h+ continuous operation)
- Database migration scenarios
- UI responsiveness with large datasets

---

## Success Criteria

### Minimum Viable Product (MVP)
1. Background daemon captures application-level usage
2. SQLite database stores at least 7 days of data
3. Web dashboard displays basic timeline and pie chart
4. Menubar icon launches dashboard
5. Auto-starts on macOS boot

### Full Feature Release
1. All visualizations implemented and interactive
2. Browser extension tracks Zen domains accurately
3. Data retention policies work as specified
4. Configuration via JSON and web UI
5. Stable for 30+ days continuous operation
6. Clear documentation for setup and usage

---

## Known Limitations & Future Work

### Current Limitations
- macOS only (not cross-platform yet)
- Requires sudo for packet sniffing (if using that method)
- Browser extension only supports Zen initially
- No historical data before installation
- Cannot retroactively analyze the 400GB mentioned

### Future Enhancements
- Cross-platform support (Linux, Windows)
- Multiple browser support
- Mobile app companion (view from phone)
- Cloud backup option (opt-in)
- Advanced filtering and search
- API for programmatic access
- Plugins/extensions system

---

## Handoff Notes for Claude Code

### Getting Started
1. Create project directory structure
2. Set up Python virtual environment
3. Install dependencies (FastAPI, Plotly, Dash, scapy/pcap, rumps, sqlite3)
4. Initialize SQLite database with schema
5. Implement core daemon loop first
6. Add web server incrementally
7. Test each component independently before integration

### Key Files to Create
- `main.py` - Entry point, orchestrates daemon + web server
- `daemon.py` - Network capture and monitoring loop
- `db_queries.py` - SQL abstraction layer
- `models.py` - Data models and schemas
- `webserver.py` - FastAPI application
- `dashboard.py` - Plotly/Dash layout and callbacks
- `menubar.py` - macOS menubar application
- `config.py` - Configuration management
- `utils.py` - Helper functions
- `schema.sql` - Database schema definition

### Extension Files (Separate Directory)
- `manifest.json` - WebExtension manifest
- `background.js` - Active tab tracking
- `api.js` - Communication with local server

### Priority Order
1. Database schema and SQL queries
2. Core daemon (packet capture)
3. Basic web server and API
4. Simple dashboard (one visualization)
5. Expand dashboard visualizations
6. MenuBar app
7. Browser extension
8. LaunchAgent and auto-start
9. Polish and error handling

### Important Considerations
- Handle sudo/root permissions gracefully
- Test database performance with large datasets
- Ensure proper cleanup on shutdown
- Make sampling interval actually configurable
- Validate all user inputs from config.json
- Handle network interface changes (WiFi → Ethernet)
- Consider IPv4 and IPv6

---

## Questions & Clarifications

If any ambiguity arises during implementation:
1. **Domain tracking:** Always prefer parent domain over subdomain
2. **Data retention:** Favor keeping more data if storage allows
3. **UI design:** Prioritize data density over aesthetics
4. **Performance:** Optimize for low resource usage over feature richness
5. **Privacy:** When in doubt, collect less data

---

## Contact & Feedback

This is a personal project for understanding network usage patterns. The spec is flexible and can evolve based on real-world usage and discoveries during development.

**User Profile:**
- Comfortable with Python and terminal work
- Prefers functional-OOP hybrid style
- Loves data transformation and pipelines
- ADHD-friendly: break into simple, focused steps
- New to FastAPI, Dash, and browser extension development

**User Preferences:**
- Small, focused functions
- Avoid complex inheritance
- Use map/filter/comprehensions over loops
- Clear data pipelines with composition

---

*Document Version: 1.0*  
*Created: November 2025*  
*Ready for handoff to Claude Code*
