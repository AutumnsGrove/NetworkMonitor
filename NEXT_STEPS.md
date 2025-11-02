# Network Monitor - Next Steps & TODOs

## 🚨 High Priority - Manual Operations Not Working

All manual operation buttons on the Config page currently show "Not Implemented" alerts:

### 1. Run Aggregation Now
**Location:** Config page → Manual Operations
**Issue:** `POST /api/config/aggregate` endpoint doesn't exist
**Code:** `src/dashboard/callbacks.py:1312-1316`
**What it should do:** Manually trigger data aggregation (hourly/daily)
**Implementation needed:**
- Create API endpoint in `src/api/config.py`
- Call `RetentionScheduler.run_aggregation()` manually
- Return success/failure status

### 2. Cleanup Old Data
**Location:** Config page → Manual Operations
**Issue:** `POST /api/config/cleanup` endpoint doesn't exist
**Code:** `src/dashboard/callbacks.py:1345-1349`
**What it should do:** Manually trigger cleanup of old data based on retention policies
**Implementation needed:**
- Create API endpoint in `src/api/config.py`
- Call `RetentionScheduler.run_cleanup()` manually
- Return rows deleted count

### 3. Refresh Cache
**Location:** Config page → Manual Operations
**Issue:** `POST /api/config/refresh-cache` endpoint doesn't exist
**Code:** `src/dashboard/callbacks.py:1378-1382`
**What it should do:** Clear internal caches (process mapper, domain cache, etc.)
**Implementation needed:**
- Create API endpoint in `src/api/config.py`
- Clear process mapper cache
- Clear domain ID cache
- Clear app ID cache

### 4. Export Data
**Location:** Config page → Manual Operations
**Issue:** `GET /api/export` endpoint doesn't exist
**Code:** `src/dashboard/callbacks.py:1411-1415`
**What it should do:** Export database to CSV/JSON format
**Implementation needed:**
- Create API endpoint that returns CSV/JSON
- Use Dash's `dcc.Download` component
- Allow selection of date range

---

## 📊 Medium Priority - Dashboard Features

### 5. Domain Timeline Not Implemented
**Location:** Domains page → Domain detail view
**Issue:** `GET /api/domains/{domain_id}/timeline` endpoint doesn't exist
**Code:** `src/dashboard/callbacks.py:747`
**What it should do:** Show hourly/daily usage timeline for specific domain
**Implementation needed:**
- Create API endpoint in `src/api/domains.py`
- Query hourly_aggregates table for domain
- Return time series data

### 6. Per-Browser Stats for Domains
**Location:** Domains page → Browser breakdown
**Issue:** No database schema for per-browser domain stats
**Code:** `src/dashboard/callbacks.py:808-815`
**What it should do:** Show which browsers accessed each domain
**Implementation needed:**
- Possibly already tracked in `browser_domain_samples` table?
- Create API endpoint to aggregate by browser
- Update dashboard callback to use real data

### 7. Browser Field Missing in Domain API
**Location:** Domains page → Application column
**Issue:** API doesn't return browser info for domains
**Code:** `src/dashboard/callbacks.py:646`
**What it should do:** Show which browser/app accessed the domain
**Implementation needed:**
- Update `GET /api/domains` endpoint
- Join with `browser_domain_samples` or applications table
- Return browser name in response

---

## 🐛 Low Priority - Polish & UX

### 8. Real-time Bandwidth Calculation
**Location:** Overview page → Current bandwidth gauge
**Issue:** Using placeholder calculation instead of real recent samples
**Code:** `src/dashboard/callbacks.py:152-161`
**What it should do:** Calculate bytes/s from last 5 seconds of samples
**Implementation needed:**
- Query samples from last 5 seconds
- Calculate delta between first and last sample
- Return accurate bytes/second

### 9. Mock Historical Data
**Location:** History page → Monthly chart
**Issue:** Using mock data instead of real monthly aggregates
**Code:** `src/dashboard/callbacks.py:1044-1053`
**What it should do:** Query real monthly data from database
**Implementation needed:**
- Create `GET /api/historical/monthly` endpoint
- Aggregate data by month
- Replace mock with API call

---

## 📝 Implementation Checklist

When implementing manual operations, follow this pattern:

```python
# src/api/config.py

@router.post("/config/aggregate")
async def trigger_aggregation():
    """Manually trigger data aggregation."""
    try:
        # Get or create scheduler instance
        scheduler = RetentionScheduler()

        # Run aggregation
        await scheduler.run_aggregation()

        return {
            "status": "success",
            "message": "Aggregation completed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

Then update the dashboard callback to use the endpoint instead of showing "Not Implemented".

---

**Last updated:** 2025-11-02
**Priority order:** Manual Operations (1-4) → Dashboard Features (5-7) → Polish (8-9)
