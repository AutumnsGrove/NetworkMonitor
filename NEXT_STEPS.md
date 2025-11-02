# Network Monitor - Next Steps & TODOs

## ✅ High Priority - Manual Operations (COMPLETED)

All manual operation buttons on the Config page are now implemented:

### 1. Run Aggregation Now ✅
**Status:** IMPLEMENTED
**Endpoint:** `POST /api/config/aggregate`
**Location:** `src/api/config.py:220-240`
**Functionality:** Manually triggers data aggregation using `aggregate_all_pending()` from retention module

### 2. Cleanup Old Data ✅
**Status:** IMPLEMENTED
**Endpoint:** `POST /api/config/cleanup`
**Location:** `src/api/config.py:243-270`
**Functionality:** Manually triggers cleanup using `cleanup_all_old_data()` with configured retention policies

### 3. Refresh Cache ✅
**Status:** IMPLEMENTED
**Endpoint:** `POST /api/config/refresh-cache`
**Location:** `src/api/config.py:273-305`
**Functionality:** Clears all internal caches (app_id_cache, domain_id_cache, process_mapper_cache)

### 4. Export Data ✅
**Status:** IMPLEMENTED
**Endpoint:** `GET /api/export`
**Location:** `src/api/config.py:308-405`
**Functionality:** Exports hourly aggregates to CSV or JSON format with optional date range filtering

---

## 📊 Medium Priority - Dashboard Features

### 5. Domain Timeline ✅
**Status:** IMPLEMENTED
**Endpoint:** `GET /api/domains/{domain_id}/timeline`
**Location:** `src/api/domains.py:155-244`
**Functionality:** Returns hourly or daily usage timeline for specific domain with configurable time periods (day/week/month)

### 6. Per-Browser Stats for Domains
**Status:** PARTIALLY IMPLEMENTED
**Note:** The `browser_domain_samples` table already tracks per-browser domain stats. A new endpoint could aggregate this data further if needed.
**Suggestion:** Use the timeline endpoint with app_id filtering or create a new endpoint `/api/domains/{domain_id}/browsers` for detailed browser breakdown

### 7. Browser Field in Domain API ✅
**Status:** IMPLEMENTED
**Location:** `src/api/domains.py:52` (response), `src/db_queries.py:481-489` (query)
**Functionality:**
- Added `browser` field to `DomainUsageStats` model
- Updated `get_domain_usage_stats()` to return primary browser (by traffic volume) for each domain
- API now returns browser/app name that accessed the domain

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
