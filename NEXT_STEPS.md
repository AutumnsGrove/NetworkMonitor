# Network Monitor - Next Steps

**Phase:** Dashboard Visualizations (Plotly/Dash)
**Goal:** Build 5 interactive web dashboard pages for visualizing network usage data
**Estimated Scope:** Dashboard implementation + testing

---

## Current Status

✅ **Backend Complete:**
- Database layer with 11 tables and retention policies
- Network capture daemon with process mapping
- FastAPI REST API with comprehensive endpoints
- 238 passing tests with 79% code coverage

🎯 **Next:** Build interactive web dashboard using Plotly and Dash

---

## Phase 5: Dashboard Visualizations (Plotly/Dash)

### Overview

Build a rich, interactive web-based dashboard that visualizes network usage data from the FastAPI backend. The dashboard will have 5 main pages with real-time updates and interactive controls.

**Technology Stack:**
- **Dash** - Dashboard framework built on Flask
- **Plotly** - Interactive charting library
- **Integration** - Mount Dash app within FastAPI application

---

## Dashboard Architecture

### Page Structure

The dashboard will have 5 main pages accessible via a navigation menu:

1. **Overview Dashboard** - Real-time usage, timeline, top apps/domains
2. **Application Details** - Per-application breakdown and timeline
3. **Domain Analysis** - Browser-specific domain tracking
4. **Historical Analysis** - Trends, heatmaps, comparisons
5. **Configuration** - Settings management and system status

### Technical Implementation

**File Structure:**
```
src/
├── dashboard.py           # Main Dash application
├── dashboard/
│   ├── __init__.py
│   ├── layouts.py         # Page layouts
│   ├── callbacks.py       # Interactivity callbacks
│   ├── components.py      # Reusable UI components
│   └── styles.py          # CSS styling
```

**Integration with FastAPI:**
- Mount Dash app at `/dashboard` route
- Keep API endpoints at `/api/*` routes
- Share database connection pool
- Use same async patterns

---

## Page 1: Overview Dashboard

**URL:** `/dashboard/` or `/dashboard/overview`

**Components:**

1. **Real-Time Gauge (Top)**
   - Current bandwidth usage (updated every 5 seconds)
   - Color-coded: Green (<1 MB/s), Yellow (1-10 MB/s), Red (>10 MB/s)
   - Plotly Gauge Chart

2. **Timeline Graph (Center)**
   - Line chart showing network usage over time
   - X-axis: Time, Y-axis: Bytes
   - Interactive time range selector (1h, 24h, 7d, 30d, 90d)
   - Zoom and pan capabilities
   - Plotly Line Chart

3. **Pie Charts (Left/Right)**
   - Left: Top 10 Applications by data usage
   - Right: Top 10 Domains by data usage
   - Click to drill down to detail pages
   - Plotly Pie Chart

4. **Quick Stats Cards (Bottom)**
   - Total data today (formatted: "5.2 GB")
   - Total data this week
   - Total data this month
   - Top application today
   - Top domain today
   - Number of active applications

**Data Sources:**
- `GET /api/stats` - Quick stats
- `GET /api/stats/timeline?period={period}` - Timeline data
- `GET /api/applications?limit=10` - Top apps
- `GET /api/domains/top/10?period=today` - Top domains

**Interactivity:**
- Time range selector updates timeline
- Click pie chart slice → Navigate to detail page
- Auto-refresh every 30 seconds (configurable)

---

## Page 2: Application Details

**URL:** `/dashboard/applications`

**Components:**

1. **Sortable Table (Top)**
   - Columns: Application Name, Bundle ID, Bytes Sent, Bytes Received, Total, Last Seen
   - Sortable by any column
   - Pagination (25 per page)
   - Search/filter bar
   - Dash DataTable

2. **Per-App Timeline (Bottom)**
   - Select application from table
   - Show timeline for selected app
   - Compare multiple apps (multi-select)
   - Plotly Line Chart

3. **Data Breakdown (Right Panel)**
   - Bytes sent vs received (stacked bar)
   - Packets sent vs received
   - Active connections over time
   - Plotly Bar Chart

**Data Sources:**
- `GET /api/applications` - List all apps
- `GET /api/applications/{app_id}` - App details
- `GET /api/applications/{app_id}/timeline` - Per-app timeline

**Interactivity:**
- Click row → Select application
- Sort columns → Re-fetch sorted data
- Search bar → Filter applications
- Multi-select → Compare apps

---

## Page 3: Domain Analysis

**URL:** `/dashboard/domains`

**Components:**

1. **Domain Hierarchy Tree (Left)**
   - Interactive tree view of parent/child domains
   - Expandable nodes (netflix.com → www.netflix.com, api.netflix.com)
   - Color-coded by usage
   - Dash Treeview or custom component

2. **Top Domains Table (Center)**
   - Similar to applications table
   - Columns: Domain, Parent Domain, Browser, Bytes, Last Seen
   - Filter by browser (Zen, Chrome, Safari)
   - Dash DataTable

3. **Domain Timeline (Bottom)**
   - Timeline for selected domain
   - Show all subdomains or parent only
   - Browser breakdown (stacked area chart)
   - Plotly Area Chart

**Data Sources:**
- `GET /api/domains` - List all domains
- `GET /api/domains?parent_only=true` - Parent domains
- `GET /api/domains/{domain_id}` - Domain details
- `GET /api/domains/top/10?period={period}` - Top domains

**Interactivity:**
- Click domain → Show timeline
- Toggle parent-only view
- Filter by browser
- Expand/collapse tree nodes

---

## Page 4: Historical Analysis

**URL:** `/dashboard/history`

**Components:**

1. **Hourly Heatmap (Top)**
   - 7 rows (days of week) × 24 columns (hours)
   - Color intensity = data usage
   - Hover for exact values
   - Plotly Heatmap

2. **Weekly Trends (Middle)**
   - Line chart comparing current week vs last week vs average
   - Identify patterns and anomalies
   - Plotly Line Chart (multiple traces)

3. **Monthly Comparison (Bottom)**
   - Bar chart comparing months
   - Year-over-year if data available
   - Plotly Bar Chart

4. **Date Range Selector (Top Right)**
   - Custom date picker
   - Presets: This Week, Last Week, This Month, Last Month
   - Dash DatePickerRange

**Data Sources:**
- `GET /api/stats/summary?since={date}` - Summary stats
- `GET /api/stats/timeline?period={period}` - Timeline data
- Database queries for aggregated hourly/daily data

**Interactivity:**
- Date range selection → Update all charts
- Hover heatmap → Show tooltip
- Click bar → Drill down to day

---

## Page 5: Configuration

**URL:** `/dashboard/config`

**Components:**

1. **System Status (Top)**
   - Daemon running status (green/red indicator)
   - Database size and path
   - Number of samples in database
   - Uptime
   - Last aggregation time

2. **Settings Form (Center)**
   - Sampling interval (1-60 seconds) - slider
   - Data retention (raw samples: 1-30 days) - slider
   - Data retention (hourly: 1-365 days) - slider
   - Web server port (7000-7999) - input
   - Log level (DEBUG, INFO, WARNING, ERROR) - dropdown
   - Save button

3. **Manual Operations (Bottom)**
   - Force aggregation now (button)
   - Clear old samples (button)
   - Refresh cache (button)
   - Export data (button)

**Data Sources:**
- `GET /api/config` - All config values
- `GET /api/config/daemon/status` - Daemon status
- `PUT /api/config` - Update config

**Interactivity:**
- Form controls update config
- Validation on save
- Manual operation buttons trigger API calls
- Success/error notifications

---

## Implementation Plan

### Step 1: Dashboard Infrastructure (Day 1)

**Tasks:**
- [ ] Create `src/dashboard.py` with basic Dash app
- [ ] Integrate Dash app with FastAPI (`app.mount()`)
- [ ] Create base layout with navigation menu
- [ ] Set up routing for 5 pages
- [ ] Add basic CSS styling

**Files:**
- `src/dashboard.py`
- `src/dashboard/__init__.py`
- `src/dashboard/layouts.py`
- `src/dashboard/styles.py`

**Test:**
- Visit `http://localhost:7500/dashboard`
- Verify navigation between pages works
- Verify FastAPI routes still work (`/api/*`)

### Step 2: Overview Dashboard (Day 2)

**Tasks:**
- [ ] Implement real-time gauge component
- [ ] Implement timeline graph with time range selector
- [ ] Implement pie charts (apps and domains)
- [ ] Implement quick stats cards
- [ ] Add auto-refresh callback (30s)

**Files:**
- `src/dashboard/layouts.py` - Overview layout
- `src/dashboard/callbacks.py` - Overview callbacks
- `src/dashboard/components.py` - Reusable components (gauge, stat card)

**Test:**
- Verify gauge shows current usage
- Verify timeline updates with time range selector
- Verify pie charts show top 10 apps/domains
- Verify auto-refresh works

### Step 3: Application Details Page (Day 3)

**Tasks:**
- [ ] Implement sortable applications table
- [ ] Implement per-app timeline graph
- [ ] Implement data breakdown charts
- [ ] Add search/filter functionality
- [ ] Add pagination

**Files:**
- `src/dashboard/layouts.py` - Applications layout
- `src/dashboard/callbacks.py` - Applications callbacks

**Test:**
- Verify table sorting works
- Verify clicking row shows timeline
- Verify search filters applications
- Verify pagination works

### Step 4: Domain Analysis Page (Day 4)

**Tasks:**
- [ ] Implement domain hierarchy tree
- [ ] Implement top domains table
- [ ] Implement domain timeline
- [ ] Add browser filtering
- [ ] Add parent-only toggle

**Files:**
- `src/dashboard/layouts.py` - Domains layout
- `src/dashboard/callbacks.py` - Domains callbacks

**Test:**
- Verify tree shows parent/child relationships
- Verify table shows all domains
- Verify browser filter works
- Verify timeline shows selected domain

### Step 5: Historical Analysis Page (Day 5)

**Tasks:**
- [ ] Implement hourly heatmap
- [ ] Implement weekly trends comparison
- [ ] Implement monthly bar chart
- [ ] Add date range picker
- [ ] Connect all charts to date range

**Files:**
- `src/dashboard/layouts.py` - History layout
- `src/dashboard/callbacks.py` - History callbacks

**Test:**
- Verify heatmap shows usage patterns
- Verify weekly trends compare correctly
- Verify date range updates all charts

### Step 6: Configuration Page (Day 6)

**Tasks:**
- [ ] Implement system status display
- [ ] Implement settings form with validation
- [ ] Implement manual operation buttons
- [ ] Add success/error notifications
- [ ] Add form validation

**Files:**
- `src/dashboard/layouts.py` - Config layout
- `src/dashboard/callbacks.py` - Config callbacks

**Test:**
- Verify status shows correct info
- Verify form saves to config
- Verify validation works
- Verify manual operations trigger

### Step 7: Polish & Testing (Day 7)

**Tasks:**
- [ ] Add responsive CSS for mobile
- [ ] Improve loading states
- [ ] Add error handling for API failures
- [ ] Test all interactivity
- [ ] Write dashboard tests
- [ ] Update documentation

**Files:**
- `src/dashboard/styles.py`
- `tests/test_dashboard.py`

**Test:**
- Full user journey testing
- Mobile responsiveness
- Error scenarios
- Performance under load

---

## Technical Details

### Dash + FastAPI Integration

**Method 1: Mount Dash as WSGI Middleware**
```python
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
import dash

app = FastAPI()
dash_app = dash.Dash(__name__, requests_pathname_prefix="/dashboard/")

# Mount Dash app
app.mount("/dashboard", WSGIMiddleware(dash_app.server))
```

**Method 2: Serve Dash within FastAPI routes**
```python
from starlette.routing import Mount
from dash import Dash

dash_app = Dash(__name__, url_base_pathname="/dashboard/")

routes = [
    Mount("/dashboard", WSGIMiddleware(dash_app.server)),
]
```

### Dash Callbacks Pattern

```python
@dash_app.callback(
    Output("timeline-graph", "figure"),
    Input("time-range-selector", "value")
)
def update_timeline(time_range):
    # Fetch data from API
    response = requests.get(f"http://localhost:7500/api/stats/timeline?period={time_range}")
    data = response.json()

    # Create Plotly figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data['timestamps'], y=data['bytes'], mode='lines'))

    return fig
```

### Data Refresh Strategy

**Option A: Auto-refresh with Interval component**
```python
dcc.Interval(id='interval-component', interval=30*1000, n_intervals=0)

@dash_app.callback(
    Output("stats-cards", "children"),
    Input("interval-component", "n_intervals")
)
def update_stats(n):
    # Fetch fresh data every 30 seconds
    return create_stats_cards()
```

**Option B: Manual refresh button**
```python
html.Button("Refresh", id="refresh-button")

@dash_app.callback(
    Output("data-display", "children"),
    Input("refresh-button", "n_clicks")
)
def refresh_data(n_clicks):
    # Fetch data on button click
    return fetch_and_display()
```

---

## Styling Approach

### CSS Framework
Use Dash Bootstrap Components for responsive layout:
```bash
pip install dash-bootstrap-components
```

```python
import dash_bootstrap_components as dbc

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
```

### Custom CSS
Create `assets/custom.css` for project-specific styling:
- Color scheme: Blues and greens for network data
- Dark mode option
- Card-based layout
- Consistent spacing

---

## Testing Strategy

### Unit Tests
- Test individual component rendering
- Test callback logic with mocked inputs
- Test data transformation functions

### Integration Tests
- Test Dash + FastAPI integration
- Test API data fetching in callbacks
- Test multi-page navigation

### Manual Tests
- User journey: Navigate all pages
- Interactivity: Click, filter, sort
- Responsiveness: Mobile, tablet, desktop
- Performance: Large datasets

---

## Success Criteria

**Phase 5 complete when:**
- ✅ All 5 dashboard pages implemented
- ✅ Navigation between pages works
- ✅ All charts display data from API correctly
- ✅ Interactive controls update charts
- ✅ Auto-refresh works on overview page
- ✅ Configuration page saves settings
- ✅ Dashboard is responsive (mobile-friendly)
- ✅ Dashboard tests pass (basic rendering tests)
- ✅ Documentation updated with screenshots

---

## After Phase 5: Next Phases

### Phase 6: MenuBar Application (rumps)
- macOS menubar icon
- Quick stats display
- Open dashboard button
- Pause/resume monitoring

### Phase 7: Browser Extension (Zen Browser)
- WebExtension for Zen browser
- Active tab tracking
- API communication
- Installation guide

### Phase 8: Main Entry Point & Integration
- Unified `main.py` entry point
- Daemon + webserver + menubar orchestration
- Graceful shutdown
- LaunchAgent setup

### Phase 9: Polish & Documentation
- README with setup instructions
- User guide
- Screenshots
- Security audit
- Performance optimization

---

**Next Command:** Start Phase 5 implementation by creating dashboard infrastructure

```bash
# Create dashboard module
mkdir -p src/dashboard
touch src/dashboard/__init__.py
touch src/dashboard/layouts.py
touch src/dashboard/callbacks.py
touch src/dashboard/components.py
touch src/dashboard/styles.py

# Install Dash dependencies
uv add dash dash-bootstrap-components
```
