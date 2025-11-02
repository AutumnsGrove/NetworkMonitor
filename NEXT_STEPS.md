# Network Monitor - Next Steps & TODOs

## 🔴 CRITICAL BUG - FIXED (2025-11-02)

### Network Capture Was Not Integrated
**Status:** ✅ FIXED (commits required)
**Severity:** CRITICAL - Application fundamentally broken
**Discovery Date:** 2025-11-02

**Problem:**
- NetworkCapture class (scapy-based) existed but was NEVER instantiated
- Daemon only used ProcessMapper (lsof) which can't measure bytes transferred
- **16,180+ samples in database, ALL with 0 bytes sent/received**
- Application was recording "which processes exist" but tracking ZERO data usage

**Root Cause:**
- daemon.py never created NetworkCapture instance
- No packet callback handler implemented
- No mapping between captured packets (IP:port) and processes

**Fix Applied:**
- Integrated NetworkCapture into NetworkDaemon class
- Added thread-safe packet callback handler
- Implemented packet-to-process mapping via (IP:port) correlation
- Added domain tracking from DNS/TLS extraction
- Graceful fallback if not running as root

**Files Modified:**
- `src/daemon.py` - Added packet capture lifecycle and byte aggregation
- `src/process_mapper.py` - Extended to track remote IP:port for correlation

**Testing Required:**
- Restart daemon with `sudo uv run python main.py`
- Verify log shows "Packet capture started successfully"
- Check new samples have bytes_sent/bytes_received > 0
- Verify domains appear in dashboard

---

## ✅ High Priority - Manual Operations (COMPLETED ✓)

**Note:** All manual operations implemented, but export endpoint had SQL bug (fixed 2025-11-02).

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
**Note:** Code has TODO comment but endpoint exists and works
**Action Required:** Remove TODO comment in `src/dashboard/callbacks.py:745-780`

### 6. Per-Browser Stats for Domains
**Status:** PARTIALLY IMPLEMENTED
**Location:** `src/dashboard/callbacks.py:806-828`
**Current:** Uses mock/placeholder data for browser breakdown
**Issue:** No API endpoint for per-browser domain statistics
**Suggestion:** Create `GET /api/domains/{domain_id}/browsers` endpoint
**Priority:** LOW (can use existing timeline with filtering)

### 7. Browser Field in Domain API ✅
**Status:** IMPLEMENTED
**Location:** `src/api/domains.py:52` (response), `src/db_queries.py:481-489` (query)
**Note:** Code has TODO comment but browser field is returned
**Action Required:** Verify and remove TODO in `src/dashboard/callbacks.py:640-646`

---

## 🐛 Low Priority - Polish & UX

### 8. Real-time Bandwidth Calculation
**Location:** Overview page → Current bandwidth gauge
**Issue:** Using PLACEHOLDER value (0.5 MB/s) instead of real calculation
**Code:** `src/dashboard/callbacks.py:155-162`
**What it should do:** Calculate bytes/s from last 5-10 seconds of packet capture stats
**Priority:** MEDIUM (user-facing feature shows fake data)

### 9. Mock Historical Data
**Location:** History page → Monthly chart
**Issue:** Using RANDOM MOCK DATA instead of real monthly aggregates
**Code:** `src/dashboard/callbacks.py:1044-1061`
**What it should do:** Query real monthly data from daily_aggregates table
**Implementation needed:**
- Use existing data or create summary endpoint
- Replace `random.uniform()` calls with real queries
**Priority:** MEDIUM (shows fake statistics to users)

### 10. Process Mapper EOF Bug
**Location:** `src/process_mapper.py` lsof parsing
**Issue:** Last process in lsof output won't be captured (no EOF handling)
**Test:** `tests/test_process_mapper.py:646` documents this bug
**Impact:** Minor - may miss last process in lsof output
**Priority:** LOW

### 11. Silent Exception Handlers
**Locations:** Multiple files have `pass` in exception handlers
**Files:**
- `src/api/config.py:73, 139`
- `src/retention.py:88, 95`
- `main.py:70`
**Issue:** Errors silently ignored without logging
**Recommendation:** Add logger.debug() or comments explaining why ignored
**Priority:** LOW

---

## 🔒 Security Vulnerabilities (Phase 10)

**Overall Security Score: 6.3/10 (D+) - MEDIUM RISK**
**Audit Date:** 2025-11-02
**Detailed Report:** See `SECURITY_AUDIT.md`

### Critical Vulnerabilities (Immediate Action Required)

#### 1. No API Authentication (CVSS 7.5) ⚠️
**Severity:** HIGH
**Impact:** Any malicious software on localhost can read browsing history, modify config, inject fake data
**Files:** All API endpoints in `src/api/*`
**Recommendation:** Implement API key authentication stored in `~/.netmonitor/api_key`
**Priority:** CRITICAL (before any deployment)

#### 2. Command Injection Risks (CVSS 8.1) ⚠️
**Severity:** HIGH
**Impact:** If port/PID inputs ever come from API, arbitrary command execution possible
**Files:** `src/process_mapper.py:83-89, 144-149, 179-184`
**Recommendation:** Add strict input validation for all subprocess parameters
**Priority:** HIGH

#### 3. SQL Injection Risks (CVSS 6.5) ⚠️
**Severity:** MEDIUM-HIGH
**Impact:** Dynamic SQL construction could allow database manipulation
**Files:** `src/db_queries.py:432-456`, `src/api/domains.py:195-224`
**Recommendation:** Use parameterized queries everywhere, whitelist table names
**Priority:** HIGH

### Medium Priority Security Issues

#### 4. Path Traversal (CVSS 5.3)
**File:** `src/process_mapper.py:176-194` (bundle ID lookup)
**Recommendation:** Validate paths are within allowed directories

#### 5. Information Disclosure (CVSS 4.3)
**File:** `src/webserver.py:66-73` (error handler)
**Recommendation:** Generic error messages in production mode

#### 6. Overly Permissive CORS (CVSS 4.0)
**File:** `src/webserver.py:55-62`
**Recommendation:** Restrict to specific ports, not wildcards

### Low Priority

7. Missing security headers
8. No input length limits
9. Logging contains sensitive data (domains, browsing history)

**Action Required:** Implement Phase 1 remediations (authentication, validation) before production use

---

## 📝 Updated Implementation Checklist

### Immediate (Next Sprint)
1. ✅ Fix network capture integration (DONE - needs testing)
2. ⬜ Implement real-time bandwidth calculation
3. ⬜ Fix historical summary mock data
4. ⬜ Remove TODO comments for completed features

### Security (Before Production)
1. ⬜ Add API authentication
2. ⬜ Validate all subprocess inputs
3. ⬜ Fix SQL injection risks
4. ⬜ Add rate limiting on POST endpoints

### Polish (Low Priority)
1. ⬜ Fix process mapper EOF handling
2. ⬜ Add logging to silent exception handlers
3. ⬜ Implement per-browser domain stats endpoint

---

**Last updated:** 2025-11-02
**Priority order:**
1. Test network capture fix (CRITICAL)
2. Security vulnerabilities (HIGH - Phase 10)
3. Dashboard polish (MEDIUM)
4. Code quality items (LOW)

**Next Steps:**
- Restart daemon to test packet capture
- Create SECURITY_AUDIT.md with full vulnerability details
- Address critical security issues before any deployment
- 24-hour stability testing with real packet capture
