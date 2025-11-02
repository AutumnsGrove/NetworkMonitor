# NetworkMonitor - Implementation TODOs

**Current Phase**: Phase 5 - Dashboard Visualizations (Plotly/Dash)
**Status**: Backend Complete (Phases 1-4), 238 tests passing, 79% coverage

---

## ✅ PHASE 1-4: COMPLETE

**Phase 1**: Database Foundation ✅
**Phase 2**: Network Capture Daemon ✅
**Phase 3**: FastAPI Server & REST API ✅
**Phase 4**: Integration Testing & Validation ✅

**Test Coverage**: 238 tests passing, 79% coverage
**Next**: Build Dashboard Visualizations

---

## PHASE 5: Dashboard Visualizations (Plotly/Dash) ⏳

### Day 1: Dashboard Infrastructure (house-coder)
- [ ] Install Dash dependencies (`uv add dash dash-bootstrap-components`)
- [ ] Create `src/dashboard/` module structure
- [ ] Create `src/dashboard/__init__.py`
- [ ] Create `src/dashboard/layouts.py` - Page layouts
- [ ] Create `src/dashboard/callbacks.py` - Interactivity callbacks
- [ ] Create `src/dashboard/components.py` - Reusable UI components
- [ ] Create `src/dashboard/styles.py` - CSS styling
- [ ] Create `src/dashboard.py` - Main Dash application
- [ ] Integrate Dash app with FastAPI (WSGIMiddleware)
- [ ] Set up base layout with navigation menu
- [ ] Set up routing for 5 pages
- [ ] Test: Visit http://localhost:7500/dashboard

### Day 2: Overview Dashboard Page (house-coder)
- [ ] Implement real-time gauge component (current bandwidth)
- [ ] Implement timeline graph with time range selector (1h, 24h, 7d, 30d, 90d)
- [ ] Implement pie charts (top 10 apps + top 10 domains)
- [ ] Implement quick stats cards (6 stats)
- [ ] Add auto-refresh callback (30 seconds interval)
- [ ] Test: Verify gauge, timeline, pie charts, stats display correctly

### Day 3: Application Details Page (house-coder)
- [ ] Implement sortable applications DataTable
- [ ] Add search/filter functionality
- [ ] Add pagination (25 per page)
- [ ] Implement per-app timeline graph
- [ ] Add multi-select for app comparison
- [ ] Implement data breakdown charts (sent/received, packets)
- [ ] Test: Verify table sorting, filtering, selection, timeline

### Day 4: Domain Analysis Page (house-coder)
- [ ] Implement domain hierarchy tree view
- [ ] Implement top domains table with browser filtering
- [ ] Add parent-only toggle
- [ ] Implement domain timeline (stacked area chart)
- [ ] Add browser breakdown visualization
- [ ] Test: Verify tree, table, filters, timeline

### Day 5: Historical Analysis Page (house-coder)
- [ ] Implement hourly heatmap (7 rows × 24 columns)
- [ ] Implement weekly trends comparison chart
- [ ] Implement monthly comparison bar chart
- [ ] Add date range picker with presets
- [ ] Connect all charts to date range updates
- [ ] Test: Verify heatmap, trends, date range updates

### Day 6: Configuration Page (house-coder)
- [ ] Implement system status display (daemon, DB size, uptime)
- [ ] Implement settings form (sliders, inputs, dropdowns)
- [ ] Add form validation
- [ ] Implement manual operation buttons (aggregation, cleanup, export)
- [ ] Add success/error notifications
- [ ] Test: Verify status display, form saves, operations trigger

### Day 7: Dashboard Testing & Polish (test-strategist → house-coder)
- [ ] Add responsive CSS for mobile/tablet
- [ ] Improve loading states
- [ ] Add error handling for API failures
- [ ] Test all interactivity
- [ ] Write `tests/test_dashboard.py`
- [ ] Test: Full user journey, mobile responsiveness, errors

---

## PHASE 6: MenuBar Application (rumps)

### Day 8: MenuBar Core (house-coder)
- [ ] Create `src/menubar.py` with rumps integration
- [ ] Add status icon (idle/low/medium/high states)
- [ ] Implement dropdown menu items
- [ ] Add current usage display (today's total)
- [ ] Test: Verify menubar appears, menu items work

### Day 9: MenuBar Integration & Testing (house-coder)
- [ ] Connect to daemon status API
- [ ] Implement "Open Dashboard" (browser launch)
- [ ] Implement pause/resume monitoring
- [ ] Add optional high-usage notifications
- [ ] Test: Verify integration with daemon, dashboard launch

---

## PHASE 7: Browser Extension (Zen Browser)

### Day 10: Extension Core (house-coder)
- [ ] Create `extension/` directory
- [ ] Create `manifest.json` (WebExtension v3)
- [ ] Create `background.js` (active tab tracking)
- [ ] Implement API communication to localhost:7500
- [ ] Test: Extension loads in Zen browser

### Day 11: Extension Testing & Packaging (house-coder)
- [ ] Add tab change detection and reporting
- [ ] Add error handling (API offline scenarios)
- [ ] Package extension for Zen
- [ ] Write installation guide
- [ ] Test: Tab tracking works, reports to API

---

## PHASE 8: Main Entry Point & Integration

### Day 12: Unified Entry Point (house-planner → house-coder)
- [ ] Plan single-process architecture (house-planner)
- [ ] Create `main.py` orchestrator
- [ ] Implement daemon + webserver + menubar coordination
- [ ] Add graceful shutdown handling (SIGTERM/SIGINT)
- [ ] Add threading/async coordination
- [ ] Test: Single command starts everything

### Day 13: LaunchAgent & Auto-Start (house-coder)
- [ ] Create LaunchAgent plist file
- [ ] Create installation script for ~/Library/LaunchAgents/
- [ ] Add startup verification and health checks
- [ ] Create uninstall script
- [ ] Test: Auto-start on macOS login works

---

## PHASE 9: Polish & Documentation

### Day 14: Final Testing & Optimization (test-strategist → security-auditor → house-coder)
- [ ] End-to-end user journey testing
- [ ] Security audit (localhost-only, file permissions)
- [ ] Performance testing (24h+ stability run)
- [ ] Memory/CPU profiling
- [ ] Fix any discovered issues
- [ ] Test: Production-ready verification

### Day 15: Documentation & Release (house-coder if requested)
- [ ] Update README.md with setup instructions (if requested)
- [ ] Create user guide with screenshots (if requested)
- [ ] Create troubleshooting guide (if requested)
- [ ] Update NEXT_STEPS.md → COMPLETED.md
- [ ] Final git commit with comprehensive message

---

## Success Criteria

**Phase 5 Complete:** 5 dashboard pages functional, responsive, tested
**Phase 6 Complete:** MenuBar app shows status, opens dashboard, controls daemon
**Phase 7 Complete:** Extension tracks Zen browser tabs, reports to API
**Phase 8 Complete:** Single command starts entire system, auto-starts on login
**Phase 9 Complete:** Security audited, 24h+ stable, documentation complete (if requested)

**Total Timeline:** 15 days (3 weeks at part-time pace)
**Total Tests Expected:** ~290 tests
**Final Coverage Target:** >80%

---

**Agent Strategy**: Extensive use of house-coder (primary), test-strategist, house-planner, security-auditor
