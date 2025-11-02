# NetworkMonitor - Implementation TODOs

**Current Phase**: Phase 1 - Integration Testing & Validation
**Status**: Backend Complete (Phases 1-3), Now Testing Before UI

---

## PHASE 1: Integration Testing & Validation ⏳

### 1.1 Test Framework Setup
- [ ] Add test dependencies to pyproject.toml (pytest-mock, httpx, pytest-cov)
- [ ] Run `uv sync` to install dependencies
- [ ] Create `tests/conftest.py` with shared fixtures
- [ ] Create `tests/fixtures.py` with mock data

### 1.2 Integration Test Suite
- [ ] Use test-strategist to plan comprehensive test scenarios
- [ ] Implement `tests/test_integration.py`
  - [ ] Database initialization flow tests
  - [ ] Daemon + Database integration tests (mocked lsof)
  - [ ] API + Database integration tests
  - [ ] Browser domain tracking flow tests
  - [ ] Retention and aggregation tests

### 1.3 API Endpoint Testing
- [ ] Implement `tests/test_api.py`
  - [ ] Stats endpoints (GET /api/stats, timeline, summary)
  - [ ] Application endpoints (list, details, timeline)
  - [ ] Domain endpoints (list, details, top domains)
  - [ ] Browser endpoints (POST active-tab, status)
  - [ ] Config endpoints (GET, PUT, init, validation)

### 1.4 Component Testing
- [ ] Implement `tests/test_process_mapper.py` (mock lsof, caching)
- [ ] Implement `tests/test_daemon.py` (lifecycle, sampling, signals)
- [ ] Expand `tests/test_utils.py` (time functions, path mgmt, validation)

### 1.5 Test Execution & Bug Fixes
- [ ] Run pytest with coverage reporting
- [ ] Fix bugs discovered during testing
- [ ] Achieve >70% test coverage
- [ ] All tests passing

---

## PHASE 2: Dashboard Visualizations (Plotly/Dash)

### 2.1 Dashboard Architecture
- [ ] Design Dash application structure (house-planner)
- [ ] Plan page routing and layouts
- [ ] Define reusable components

### 2.2 Core Dashboard Infrastructure
- [ ] Create `src/dashboard.py` with Dash app setup
- [ ] Integrate Dash with FastAPI server
- [ ] Add base layout and navigation

### 2.3 Page 1 - Overview Dashboard
- [ ] Timeline graph (24h, 7d, 30d views)
- [ ] Pie chart (application breakdown)
- [ ] Real-time usage gauge
- [ ] Top domains table
- [ ] Quick stats cards

### 2.4 Page 2 - Application Details
- [ ] Sortable application table
- [ ] Per-app timeline graphs
- [ ] Data sent/received breakdown
- [ ] Process details display

### 2.5 Page 3 - Domain Analysis
- [ ] Browser-specific domain breakdown
- [ ] Top domains visualization
- [ ] Domain timeline tracking
- [ ] Subdomain rollup display

### 2.6 Page 4 - Historical Analysis
- [ ] Hourly heatmap (day × hour)
- [ ] Weekly trends graph
- [ ] Monthly comparisons
- [ ] Customizable date range selector

### 2.7 Page 5 - Configuration
- [ ] Sampling interval controls
- [ ] Data retention policy settings
- [ ] Log level configuration
- [ ] System status display

---

## PHASE 3: MenuBar Application (rumps)

### 3.1 MenuBar Design
- [ ] Design menu structure and status icons (house-planner)
- [ ] Plan daemon communication strategy

### 3.2 MenuBar Implementation
- [ ] Create `src/menubar.py` with rumps
- [ ] Add status icon with activity indicator
- [ ] Implement dropdown menu (stats, open dashboard, pause/resume, quit)
- [ ] Add notification support for high usage

---

## PHASE 4: Browser Extension (Zen Browser)

### 4.1 Extension Architecture
- [ ] Design WebExtension structure (house-planner)
- [ ] Plan API communication protocol

### 4.2 Extension Implementation
- [ ] Create `extension/` directory
- [ ] Implement `manifest.json` for Zen browser
- [ ] Create `background.js` for active tab tracking
- [ ] Add API communication to localhost:7500
- [ ] Write installation instructions

---

## PHASE 5: Configuration & Lifecycle Management

### 5.1 Logging Configuration
- [ ] Create `src/logging_config.py`
- [ ] Set up log rotation (daemon.log, webserver.log)
- [ ] Add log level management

### 5.2 Config Initialization
- [ ] Ensure `~/.netmonitor/config.json` created on first run
- [ ] Add config validation and migration
- [ ] Update config API to handle file creation

### 5.3 LaunchAgent Setup
- [ ] Create `com.networkmonitor.daemon.plist` template
- [ ] Add installation script
- [ ] Document auto-start setup

---

## PHASE 6: Main Entry Point & Integration

### 6.1 Main Architecture Design
- [ ] Design single-process architecture (house-planner)
- [ ] Plan daemon + webserver + menubar coordination
- [ ] Define startup/shutdown sequences

### 6.2 Main Implementation
- [ ] Create `main.py` as unified entry point
- [ ] Orchestrate daemon, webserver, dashboard, menubar
- [ ] Add graceful shutdown handlers (SIGTERM/SIGINT)
- [ ] Implement health checks

### 6.3 Error Handling & Recovery
- [ ] Add comprehensive error handling
- [ ] Implement crash recovery
- [ ] Add restart logic for failed components

### 6.4 Final Integration Tests
- [ ] End-to-end testing of complete application
- [ ] Long-running stability tests (24+ hours)
- [ ] Resource usage validation

---

## PHASE 7: Documentation & Security

### 7.1 Documentation Update
- [ ] Update README.md with installation instructions
- [ ] Document configuration options
- [ ] Add troubleshooting guide
- [ ] Create user guide for dashboard

### 7.2 Security Audit
- [ ] Review authentication (localhost-only binding)
- [ ] Check file permissions (database 600)
- [ ] Validate no secrets in code
- [ ] Review error messages for information leakage

### 7.3 Final Review & Commit
- [ ] Review all changes across phases
- [ ] Prepare comprehensive commit messages
- [ ] Update SO_FAR.md with final status
- [ ] Tag release version 0.1.0

---

## Success Criteria

**Phase 1 Complete When:**
- ✅ All integration tests pass
- ✅ All API endpoint tests pass
- ✅ All component tests pass
- ✅ Test coverage >70%
- ✅ Manual curl tests succeed
- ✅ All critical bugs fixed

**Full Project Complete When:**
- ✅ All tests pass (>70% coverage)
- ✅ Dashboard displays live data
- ✅ MenuBar app launches and controls daemon
- ✅ Browser extension tracks domains
- ✅ Auto-starts on macOS boot
- ✅ Runs stably for 24+ hours
- ✅ Documentation complete
- ✅ Security audit passed

---

**Estimated Timeline**: 15-22 sessions
**Agent Strategy**: Extensive use of house-coder, house-planner, test-strategist, bash-executor
