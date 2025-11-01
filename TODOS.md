# TODOs for NetworkMonitor

## Phase 1: Database Foundation (Agent 1)
- [ ] Create database schema (`schema.sql`) with all required tables
- [ ] Implement SQL abstraction layer (`src/db_queries.py`)
- [ ] Create Pydantic data models (`src/models.py`)
- [ ] Implement data retention and migration logic
- [ ] Set up `~/.netmonitor/` directory structure

## Phase 2: Network Capture Daemon (Agent 2)
- [ ] Implement packet capture using scapy (`src/capture.py`)
- [ ] Create main daemon loop with 5-second sampling (`src/daemon.py`)
- [ ] Add process/application identification
- [ ] Implement data aggregation (raw → hourly) (`src/aggregator.py`)
- [ ] Add graceful shutdown handling

## Phase 3: FastAPI Server & API (Agent 3)
- [ ] Set up FastAPI application (`src/webserver.py`)
- [ ] Implement REST API endpoints (`src/api/routes.py`)
- [ ] Create `/api/stats` endpoint for current/historical stats
- [ ] Create `/api/applications` endpoint for app usage data
- [ ] Create `/api/domains` endpoint for browser domain data
- [ ] Create `/api/browser/active-tab` endpoint for extension

## Phase 4: Dashboard Visualizations (Agent 4)
- [ ] Create Plotly/Dash dashboard layout (`src/dashboard.py`)
- [ ] Implement overview page (timeline, pie chart, gauges)
- [ ] Implement application details page
- [ ] Implement domain analysis page
- [ ] Implement historical analysis page with heatmaps
- [ ] Add configuration page

## Phase 5: MenuBar Application (Agent 5)
- [ ] Implement macOS menubar app using rumps (`src/menubar.py`)
- [ ] Add status icon with activity indication
- [ ] Create dropdown menu with quick stats
- [ ] Add "Open Dashboard" functionality
- [ ] Add pause/resume controls

## Phase 6: Browser Extension (Agent 6)
- [ ] Create WebExtension manifest for Zen browser
- [ ] Implement active tab tracking (JavaScript)
- [ ] Add API communication to local server
- [ ] Write extension installation instructions

## Phase 7: Configuration & Lifecycle (Agent 7)
- [ ] Create configuration management (`src/config.py`)
- [ ] Generate default `config.json` in `~/.netmonitor/`
- [ ] Create LaunchAgent plist file for auto-start
- [ ] Set up logging with rotation
- [ ] Add graceful shutdown and cleanup

## Phase 8: Integration & Polish (Agent 8)
- [ ] Create main entry point orchestrating all components (`main.py`)
- [ ] Add error handling and recovery
- [ ] Implement health checks
- [ ] Write comprehensive README
- [ ] Test end-to-end functionality
