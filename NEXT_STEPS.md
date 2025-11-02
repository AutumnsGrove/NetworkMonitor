# Network Monitor - Next Steps

**Phase:** Integration Testing & Validation
**Goal:** Test and validate all backend components before building UI
**Estimated Scope:** Testing framework setup + integration tests + bug fixes

---

## Immediate Priority: Integration Testing

Before moving to Phase 4 (Dashboard), we need to ensure the backend works end-to-end. This means testing the complete flow:

1. Daemon samples network → 2. Data stored in DB → 3. API serves data → 4. Tests verify correctness

---

## Testing Strategy

### 1. Test Framework Setup

**Goal:** Expand test infrastructure beyond database unit tests

**Tasks:**
- [ ] Add `pytest-mock` for mocking system calls (lsof, subprocess)
- [ ] Add `httpx` for async HTTP client testing (FastAPI endpoints)
- [ ] Add `pytest-cov` for test coverage reporting
- [ ] Create `tests/conftest.py` with shared fixtures
- [ ] Set up test database fixtures (already have temp_db)
- [ ] Create mock process fixtures for testing

**New Dependencies to Add:**
```toml
"pytest-mock>=3.12.0",
"httpx>=0.25.0",
"pytest-cov>=4.1.0",
```

---

### 2. Integration Test Suite

**Goal:** Test complete workflows from capture → storage → API

#### Test Module: `tests/test_integration.py`

**Scenarios to Test:**

1. **Database Initialization Flow**
   - [ ] Test `~/.netmonitor/` directory creation
   - [ ] Test database initialization with schema
   - [ ] Test config table population
   - [ ] Verify file permissions (600 for DB)

2. **Daemon + Database Integration**
   - [ ] Test daemon starts and stops gracefully
   - [ ] Test process mapper finds network processes (mock lsof)
   - [ ] Test network samples are inserted into database
   - [ ] Test app_id caching works
   - [ ] Test retention scheduler runs aggregation
   - [ ] Test cleanup operations execute

3. **API + Database Integration**
   - [ ] Test GET /api/stats returns valid data
   - [ ] Test GET /api/applications lists apps
   - [ ] Test GET /api/domains lists domains
   - [ ] Test POST /api/browser/active-tab creates records
   - [ ] Test GET /health shows daemon status
   - [ ] Test all endpoints with empty database
   - [ ] Test all endpoints with sample data

4. **Browser Domain Tracking Flow**
   - [ ] Test browser extension POST creates domain
   - [ ] Test parent domain rollup works correctly
   - [ ] Test domain appears in /api/domains
   - [ ] Test browser_domain_samples table populated

5. **Retention and Aggregation**
   - [ ] Test hourly aggregation creates correct records
   - [ ] Test daily aggregation creates correct records
   - [ ] Test old sample cleanup deletes correct records
   - [ ] Test retention_log tracks operations

---

### 3. API Endpoint Testing

**Goal:** Validate all REST endpoints work correctly

#### Test Module: `tests/test_api.py`

**Test Each Endpoint:**

**Stats Endpoints:**
- [ ] `GET /api/stats` - Returns quick stats structure
- [ ] `GET /api/stats/timeline?period=24h` - Returns timeline data
- [ ] `GET /api/stats/summary` - Returns summary

**Application Endpoints:**
- [ ] `GET /api/applications` - Lists applications
- [ ] `GET /api/applications?limit=10&since=2024-01-01` - Filters work
- [ ] `GET /api/applications/{app_id}` - Returns app details
- [ ] `GET /api/applications/999` - Returns 404 for missing app
- [ ] `GET /api/applications/{app_id}/timeline` - Returns timeline

**Domain Endpoints:**
- [ ] `GET /api/domains` - Lists domains
- [ ] `GET /api/domains?parent_only=true` - Filters to parent domains
- [ ] `GET /api/domains/{domain_id}` - Returns domain details
- [ ] `GET /api/domains/top/10?period=today` - Returns top domains

**Browser Endpoints:**
- [ ] `POST /api/browser/active-tab` - Accepts valid report
- [ ] `POST /api/browser/active-tab` - Rejects invalid report
- [ ] `GET /api/browser/status` - Returns status

**Config Endpoints:**
- [ ] `GET /api/config` - Returns all config
- [ ] `GET /api/config/sampling_interval_seconds` - Returns specific value
- [ ] `PUT /api/config` - Updates value
- [ ] `PUT /api/config` - Validates port range (7000-7999)
- [ ] `PUT /api/config` - Validates interval range (1-60)
- [ ] `GET /api/config/daemon/status` - Returns daemon status
- [ ] `POST /api/config/init` - Creates config.json

---

### 4. Process Mapper Testing

**Goal:** Validate process identification works (with mocks)

#### Test Module: `tests/test_process_mapper.py`

**Tests:**
- [ ] Mock lsof output for process lookup
- [ ] Test `get_process_for_connection()` with cached entry
- [ ] Test `get_process_for_connection()` with lsof lookup
- [ ] Test `get_all_network_processes()` parses lsof correctly
- [ ] Test bundle ID extraction from .app path
- [ ] Test cache clearing and refresh
- [ ] Test timeout handling

---

### 5. Daemon Testing

**Goal:** Validate daemon lifecycle and sampling

#### Test Module: `tests/test_daemon.py`

**Tests:**
- [ ] Test daemon initialization
- [ ] Test daemon start and stop
- [ ] Test signal handlers (SIGTERM, SIGINT)
- [ ] Test sampling loop executes
- [ ] Test `record_browser_domain()` creates records
- [ ] Test `get_status()` returns correct info
- [ ] Test error handling in sampling loop
- [ ] Test retention scheduler integration

---

### 6. Utility Function Testing

**Goal:** Comprehensive validation of utility functions

#### Test Module: `tests/test_utils.py`

**Already tested in test_database.py:**
- [x] `extract_parent_domain()`
- [x] `normalize_domain()`
- [x] `get_domain_with_parent()`
- [x] `format_bytes()`
- [x] `format_rate()`

**Still need tests for:**
- [ ] `round_to_hour()`
- [ ] `round_to_day()`
- [ ] `get_time_ranges()`
- [ ] `get_hours_to_aggregate()`
- [ ] `get_days_to_aggregate()`
- [ ] `format_duration()`
- [ ] All path management functions
- [ ] All validation functions

---

## Manual Testing Plan

### Test 1: Database Setup
```bash
# Test database initialization
uv run python -c "from src.db_queries import init_database; init_database()"

# Verify directory created
ls -la ~/.netmonitor/

# Verify database created
ls -la ~/.netmonitor/network_monitor.db

# Check permissions
stat -f "%A" ~/.netmonitor/network_monitor.db  # Should be 600
```

### Test 2: API Server Startup
```bash
# Start the API server
uv run python -m src.webserver

# In another terminal, test health check
curl http://127.0.0.1:7500/health

# Test API docs
open http://127.0.0.1:7500/docs

# Test stats endpoint
curl http://127.0.0.1:7500/api/stats | jq
```

### Test 3: Browser Extension Endpoint
```bash
# Test posting active tab
curl -X POST http://127.0.0.1:7500/api/browser/active-tab \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "netflix.com",
    "timestamp": 1699123456,
    "browser": "zen"
  }' | jq

# Verify domain appears in API
curl http://127.0.0.1:7500/api/domains | jq
```

### Test 4: Config Management
```bash
# Initialize config
curl -X POST http://127.0.0.1:7500/api/config/init | jq

# Check config file created
cat ~/.netmonitor/config.json

# Get config via API
curl http://127.0.0.1:7500/api/config | jq

# Update config
curl -X PUT http://127.0.0.1:7500/api/config \
  -H "Content-Type: application/json" \
  -d '{"key": "sampling_interval_seconds", "value": "10"}' | jq
```

---

## Mock Data Setup

Create test data fixtures for realistic testing:

**File: `tests/fixtures.py`**

**Contents:**
- Sample network processes (process names, PIDs, bundle IDs)
- Sample domains (parent/child relationships)
- Sample network samples (realistic byte counts)
- Sample lsof output (for mocking)
- Sample config values

---

## Bug Fixes & Improvements to Address

### Issues Found During Review:

1. **`src/webserver.py` - Import Order Issue:**
   - API routers imported before they're created
   - Need to ensure all `src/api/*.py` files exist
   - Fixed: All files created ✅

2. **Daemon Byte Counting:**
   - Current implementation doesn't track actual bytes (lsof limitation)
   - Would need packet capture integration for real counts
   - **Action:** Document limitation, test with zero/mock values

3. **Signal Handlers in Daemon:**
   - Signal handlers create async tasks but aren't awaited
   - **Action:** Review signal handling, ensure proper shutdown

4. **Config File Initialization:**
   - Config API can create config.json but daemon doesn't
   - **Action:** Ensure `~/.netmonitor/config.json` created on first run

5. **Logging Configuration:**
   - No logging setup yet
   - **Action:** Create logging configuration module

---

## Pre-Phase 4 Checklist

Before starting Phase 4 (Dashboard Visualizations), ensure:

- [ ] All integration tests pass
- [ ] API endpoints tested manually with curl
- [ ] Database operations verified
- [ ] `~/.netmonitor/` directory structure created
- [ ] Config initialization works
- [ ] Daemon can start/stop gracefully
- [ ] Health check endpoint reports correct status
- [ ] Browser extension endpoint accepts and stores data
- [ ] Retention scheduler doesn't crash
- [ ] Test coverage >70% for critical paths
- [ ] All known bugs fixed or documented
- [ ] SO_FAR.md updated with test results

---

## Test Execution Plan

**Day 1: Test Framework Setup**
1. Add new test dependencies to pyproject.toml
2. Run `uv sync`
3. Create `tests/conftest.py` with fixtures
4. Create `tests/fixtures.py` with mock data
5. Verify pytest runs all existing tests

**Day 2: Integration Tests**
1. Write `tests/test_integration.py`
2. Test daemon + database flow
3. Test API + database flow
4. Test browser domain tracking
5. Run tests, fix failures

**Day 3: API Endpoint Tests**
1. Write `tests/test_api.py`
2. Test all endpoints with httpx
3. Test error cases (404s, validation)
4. Run tests, fix failures

**Day 4: Component Tests**
1. Write `tests/test_process_mapper.py`
2. Write `tests/test_daemon.py`
3. Expand `tests/test_utils.py`
4. Run all tests, ensure >70% coverage

**Day 5: Manual Testing & Bug Fixes**
1. Run manual test plan (above)
2. Fix any issues discovered
3. Update documentation
4. Commit all changes

---

## Commands to Run

### Install Test Dependencies
```bash
# Add to pyproject.toml dependencies
# Then run:
uv sync
```

### Run All Tests
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html --cov-report=term

# Run specific test file
uv run pytest tests/test_integration.py -v

# Run specific test
uv run pytest tests/test_api.py::test_stats_endpoint -v
```

### Manual API Testing
```bash
# Start server in background
uv run python -m src.webserver &

# Run tests
./scripts/test_api.sh  # (create this script)

# Stop server
pkill -f "python -m src.webserver"
```

---

## Success Criteria

**Integration testing phase is complete when:**

1. ✅ All existing tests still pass (20 database tests)
2. ✅ All new integration tests pass (target: 30+ tests)
3. ✅ All API endpoints tested (target: 20+ endpoint tests)
4. ✅ Manual curl tests all succeed
5. ✅ Test coverage >70% for src/ directory
6. ✅ Daemon starts, samples, and stops without errors
7. ✅ API serves data from database correctly
8. ✅ Browser extension endpoint works end-to-end
9. ✅ Config management works (read/write config.json)
10. ✅ Retention scheduler doesn't crash
11. ✅ All critical bugs fixed
12. ✅ Documentation updated

---

## After Testing: Phase 4 Preparation

Once integration testing is complete:

**Phase 4: Dashboard Visualizations (Plotly/Dash)**

We'll build 5 interactive pages:
1. Overview Dashboard (timeline, pie chart, gauges, stats)
2. Application Details (sortable tables, per-app graphs)
3. Domain Analysis (browser-specific breakdown)
4. Historical Analysis (heatmaps, trends, comparisons)
5. Configuration (settings management UI)

But first: **Let's make sure the backend is rock solid!**

---

**Next Command:** Add test dependencies and create test fixtures
```bash
# Edit pyproject.toml to add:
# "pytest-mock>=3.12.0"
# "httpx>=0.25.0"
# "pytest-cov>=4.1.0"

uv sync
```

Then start writing integration tests in `tests/test_integration.py`.
