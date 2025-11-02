# Network Monitor - Agentic Development Guide

## Development Strategy

Break project into independent subagent tasks to avoid context pollution. Each subagent gets the full spec + their specific task.

---

## Subagent Task Breakdown

### Agent 1: Database Foundation
**Task:** Create database schema, SQL abstraction layer, and data models
**Deliverables:**
- `schema.sql` - Complete database schema
- `db_queries.py` - All SQL operations abstracted
- `models.py` - Pydantic models for data structures
- Migration logic for data retention policies

### Agent 2: Network Capture Daemon
**Task:** Implement core monitoring loop with packet capture
**Deliverables:**
- `daemon.py` - Main capture loop (5-second sampling)
- `capture.py` - Packet sniffing or lsof implementation
- `aggregator.py` - Data aggregation logic (raw → hourly)
- Process/application identification

### Agent 3: FastAPI Server & API
**Task:** Build web server and REST endpoints
**Deliverables:**
- `webserver.py` - FastAPI application setup
- `api/routes.py` - All API endpoints
- `/api/stats` - Current/historical stats
- `/api/applications` - App usage data
- `/api/domains` - Browser domain data
- `/api/browser/active-tab` - Extension endpoint
- `/api/config` - Configuration management

### Agent 4: Dashboard Visualizations
**Task:** Create Plotly/Dash dashboard with all visualizations
**Deliverables:**
- `dashboard.py` - Dash app layout and callbacks
- Overview page (timeline, pie chart, gauges, stats)
- Application details page
- Domain analysis page
- Historical analysis (heatmaps, trends)
- Configuration page
- Real-time updates via websockets/polling

### Agent 5: MenuBar Application
**Task:** macOS menubar integration
**Deliverables:**
- `menubar.py` - rumps menubar app
- Status icon with activity indication
- Dropdown menu with quick stats
- Open dashboard functionality
- Pause/resume controls

### Agent 6: Browser Extension
**Task:** Zen browser WebExtension
**Deliverables:**
- `extension/manifest.json`
- `extension/background.js` - Active tab tracking
- `extension/api.js` - Local API communication
- Installation instructions

### Agent 7: Configuration & Lifecycle
**Task:** Config management and auto-start
**Deliverables:**
- `config.py` - Config parsing and validation
- Default `config.json`
- LaunchAgent plist file
- Logging setup (rotating file handlers)
- Graceful shutdown handling

### Agent 8: Integration & Main Entry
**Task:** Orchestrate all components
**Deliverables:**
- `main.py` - Entry point that starts daemon + web server + menubar
- Error handling and recovery
- Component initialization order
- Health checks

---

## Execution Order

1. **Agent 1** (Database) - Foundation for everything
2. **Agent 2** (Daemon) - Core functionality
3. **Agent 3** (API) - Connects daemon to frontend
4. **Agent 4** (Dashboard) - User interface
5. **Agent 5** (MenuBar) - System integration
6. **Agent 6** (Extension) - Browser tracking
7. **Agent 7** (Config/Lifecycle) - Production readiness
8. **Agent 8** (Integration) - Tie everything together

---

## Integration Points

### Between Agents
- **1→2:** Database writes from daemon
- **2→3:** Daemon data served via API
- **3→4:** API endpoints consumed by dashboard
- **3→6:** Browser extension posts to API
- **5→4:** MenuBar opens dashboard
- **7→All:** Config used by all components
- **8→All:** Main orchestrates everything

### Shared Dependencies
Initialize with `uv` and create `pyproject.toml`:
```toml
[project]
name = "network-monitor"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "fastapi",
    "uvicorn[standard]",
    "plotly",
    "dash",
    "scapy",  # or psutil for lsof approach
    "rumps",
    "pydantic",
    "aiosqlite",
    "python-multipart",
]
```

### Shared Utilities
Create `utils.py` early for:
- Domain rollup function
- Timestamp helpers
- Data formatting
- File path management (`~/.netmonitor/`)

---

## Testing Strategy

Each agent should include basic tests:
- Agent 1: Test SQL queries, schema creation
- Agent 2: Mock network capture, test aggregation
- Agent 3: Test API endpoints with mock data
- Agent 4: Manual browser testing
- Agent 5: Manual macOS testing
- Agent 6: Extension load testing in Zen
- Agent 7: Test config parsing, LaunchAgent
- Agent 8: End-to-end integration test

---

## Prompt Template for Each Subagent

```
You are Agent [N] working on the Network Monitor project.

**Full Spec:** [Attach network-monitor-spec.md]

**Your Task:** [Specific agent task from above]

**Deliverables:** [List files from above]

**Integration Notes:**
- Database location: ~/.netmonitor/network_monitor.db
- Config location: ~/.netmonitor/config.json
- Port: 7500 (from config)
- Sampling interval: 5 seconds (from config)

**Code Style Preferences:**
- Functional-OOP hybrid
- Small, focused functions
- Use map/filter/comprehensions over loops
- Clear data pipelines
- Avoid complex inheritance

**Critical Requirements:**
[Any specific requirements for this agent]

Begin implementation.
```

---

## Success Criteria

After all agents complete:
- ✓ Daemon captures network usage every 5 seconds
- ✓ SQLite stores data with retention policy
- ✓ Web dashboard shows all visualizations at localhost:7500
- ✓ MenuBar icon launches dashboard
- ✓ Browser extension tracks Zen domains
- ✓ Auto-starts via LaunchAgent
- ✓ Config adjustable via config.json

---

## Quick Start Command

After all development:
```bash
# Initialize project with uv
uv sync

# Run (will create ~/.netmonitor/ on first run)
sudo uv run python main.py  # sudo needed for packet capture

# Or via LaunchAgent after setup
launchctl load ~/Library/LaunchAgents/com.networkmonitor.daemon.plist
```

---

*Agentic Guide v1.0 - Keep each agent focused on their deliverables*
