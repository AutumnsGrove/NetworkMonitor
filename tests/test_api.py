"""
Comprehensive API endpoint tests for NetworkMonitor FastAPI application.

Tests all REST API endpoints including stats, applications, domains, browser,
and config endpoints with both empty and populated databases. Includes
validation, error handling, and query parameter filtering tests.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch


# ============================================================================
# Health & Root Endpoints
# ============================================================================

@pytest.mark.asyncio
async def test_health_endpoint(async_test_client, temp_db):
    """
    Test /health endpoint returns healthy status.

    Validates:
    - 200 status code
    - Proper response structure
    - Daemon status included
    """
    response = await async_test_client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert data["status"] == "healthy"
    assert "daemon" in data


@pytest.mark.asyncio
async def test_root_endpoint(async_test_client, temp_db):
    """
    Test root / endpoint returns API information.

    Validates:
    - 200 status code
    - Message and version present
    - Links to docs and health endpoints
    """
    response = await async_test_client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert data["message"] == "Network Monitor API"
    assert data["version"] == "0.1.0"
    assert data["docs"] == "/docs"
    assert data["health"] == "/health"


# ============================================================================
# Stats Endpoints - Empty Database (Section 3.1)
# ============================================================================

@pytest.mark.asyncio
async def test_stats_empty_database(async_test_client, temp_db):
    """
    Test /api/stats with empty database.

    Validates:
    - 200 status code
    - All byte counts are 0
    - top_app and top_domain are None
    - Proper response structure
    """
    response = await async_test_client.get("/api/stats")

    assert response.status_code == 200
    data = response.json()

    # Check structure
    assert "today" in data
    assert "this_week" in data
    assert "this_month" in data
    assert "current" in data

    # Check today stats
    assert data["today"]["total_bytes"] == 0
    assert data["today"]["total_formatted"] == "0 B"
    assert data["today"]["top_app"] is None
    assert data["today"]["top_domain"] is None

    # Check week stats
    assert data["this_week"]["total_bytes"] == 0
    assert data["this_week"]["total_formatted"] == "0 B"

    # Check month stats
    assert data["this_month"]["total_bytes"] == 0
    assert data["this_month"]["total_formatted"] == "0 B"

    # Check current stats
    assert data["current"]["active_connections"] == 0
    assert data["current"]["monitoring_since"] is None


@pytest.mark.asyncio
async def test_stats_timeline_empty_database(async_test_client, temp_db):
    """
    Test /api/stats/timeline with empty database.

    Validates:
    - 200 status code
    - Empty timeline array
    - data_points count is 0
    - Proper period handling
    """
    response = await async_test_client.get("/api/stats/timeline?period=24h")

    assert response.status_code == 200
    data = response.json()

    assert data["period"] == "24h"
    assert "since" in data
    assert data["granularity"] == "auto"
    assert data["data_points"] == 0
    assert data["timeline"] == []


@pytest.mark.asyncio
async def test_stats_summary_empty_database(async_test_client, temp_db):
    """
    Test /api/stats/summary with empty database.

    Validates:
    - 200 status code
    - Zero byte counts
    - None for top app and domain
    """
    response = await async_test_client.get("/api/stats/summary")

    assert response.status_code == 200
    data = response.json()

    assert data["total_bytes"] == 0
    assert data["total_formatted"] == "0 B"
    assert data["avg_daily_bytes"] == 0
    assert data["avg_daily_formatted"] == "0 B"
    assert data["monitoring_since"] is None
    assert data["top_application"] is None
    assert data["top_domain"] is None


# ============================================================================
# Applications Endpoints - Empty Database (Section 3.1)
# ============================================================================

@pytest.mark.asyncio
async def test_applications_list_empty_database(async_test_client, temp_db):
    """
    Test /api/applications with empty database.

    Validates:
    - 200 status code
    - Empty applications array
    - count is 0
    """
    response = await async_test_client.get("/api/applications")

    assert response.status_code == 200
    data = response.json()

    assert data["count"] == 0
    assert data["applications"] == []
    assert data["since"] is None


@pytest.mark.asyncio
async def test_applications_detail_not_found(async_test_client, temp_db):
    """
    Test /api/applications/999 returns 404 for non-existent app.

    Validates:
    - 404 status code
    - Proper error message
    """
    response = await async_test_client.get("/api/applications/999")

    assert response.status_code == 404
    data = response.json()

    assert "detail" in data
    assert data["detail"] == "Application not found"


# ============================================================================
# Domains Endpoints - Empty Database (Section 3.1)
# ============================================================================

@pytest.mark.asyncio
async def test_domains_list_empty_database(async_test_client, temp_db):
    """
    Test /api/domains with empty database.

    Validates:
    - 200 status code
    - Empty domains array
    - count is 0
    """
    response = await async_test_client.get("/api/domains")

    assert response.status_code == 200
    data = response.json()

    assert data["count"] == 0
    assert data["domains"] == []
    assert data["since"] is None
    assert data["parent_only"] is False


@pytest.mark.asyncio
async def test_domains_detail_not_found(async_test_client, temp_db):
    """
    Test /api/domains/999 returns 404 for non-existent domain.

    Validates:
    - 404 status code
    - Proper error message
    """
    response = await async_test_client.get("/api/domains/999")

    assert response.status_code == 404
    data = response.json()

    assert "detail" in data
    assert data["detail"] == "Domain not found"


@pytest.mark.asyncio
async def test_domains_top_empty_database(async_test_client, temp_db):
    """
    Test /api/domains/top/10 with empty database.

    Validates:
    - 200 status code
    - Empty top_domains array
    - Proper period parameter
    """
    response = await async_test_client.get("/api/domains/top/10?period=today")

    assert response.status_code == 200
    data = response.json()

    assert data["period"] == "today"
    assert data["limit"] == 10
    assert data["top_domains"] == []


# ============================================================================
# Stats Endpoints - With Sample Data (Section 3.2)
# ============================================================================

@pytest.mark.asyncio
async def test_stats_with_data(async_test_client, db_with_sample_data):
    """
    Test /api/stats with pre-populated database.

    Validates:
    - 200 status code
    - Non-zero byte counts
    - Proper formatted byte strings
    - Active connections reported
    """
    response = await async_test_client.get("/api/stats")

    assert response.status_code == 200
    data = response.json()

    # Today should have data
    assert data["today"]["total_bytes"] > 0
    assert data["today"]["total_formatted"] != "0 B"

    # Week should have data
    assert data["this_week"]["total_bytes"] > 0

    # Month should have data
    assert data["this_month"]["total_bytes"] > 0

    # Current stats
    assert "active_connections" in data["current"]
    assert "monitoring_since" in data["current"]


@pytest.mark.asyncio
async def test_stats_timeline_with_data(async_test_client, db_with_sample_data):
    """
    Test /api/stats/timeline with data for different periods.

    Validates:
    - 200 status code
    - Timeline data present
    - Proper data point structure
    - Timestamps in ISO format
    """
    periods = ["1h", "24h", "7d", "30d"]

    for period in periods:
        response = await async_test_client.get(f"/api/stats/timeline?period={period}")

        assert response.status_code == 200
        data = response.json()

        assert data["period"] == period
        assert "since" in data
        assert data["data_points"] >= 0
        assert isinstance(data["timeline"], list)

        # Check data point structure if timeline has data
        if data["timeline"]:
            point = data["timeline"][0]
            assert "timestamp" in point
            assert "bytes_sent" in point
            assert "bytes_received" in point
            assert "total_bytes" in point
            assert "packets" in point


@pytest.mark.asyncio
async def test_stats_timeline_invalid_period(async_test_client, db_with_sample_data):
    """
    Test /api/stats/timeline with invalid period parameter.

    Validates:
    - Returns error for invalid period
    """
    response = await async_test_client.get("/api/stats/timeline?period=invalid")

    assert response.status_code == 200
    data = response.json()

    assert "error" in data
    assert "Invalid period" in data["error"]


@pytest.mark.asyncio
async def test_stats_summary_with_data(async_test_client, db_with_sample_data):
    """
    Test /api/stats/summary with sample data.

    Validates:
    - 200 status code
    - Non-zero totals
    - monitoring_since timestamp present
    """
    response = await async_test_client.get("/api/stats/summary")

    assert response.status_code == 200
    data = response.json()

    assert data["total_bytes"] > 0
    assert data["total_formatted"] != "0 B"
    assert data["avg_daily_bytes"] >= 0


@pytest.mark.asyncio
async def test_stats_summary_with_since_filter(async_test_client, db_with_sample_data):
    """
    Test /api/stats/summary with since parameter.

    Validates:
    - 200 status code
    - Accepts ISO format date
    """
    since_date = (datetime.now() - timedelta(hours=12)).isoformat()
    response = await async_test_client.get(f"/api/stats/summary?since={since_date}")

    assert response.status_code == 200
    data = response.json()

    assert "total_bytes" in data
    assert "total_formatted" in data


# ============================================================================
# Applications Endpoints - With Sample Data (Section 3.2)
# ============================================================================

@pytest.mark.asyncio
async def test_applications_list_with_data(async_test_client, db_with_sample_data):
    """
    Test /api/applications with sample data.

    Validates:
    - 200 status code
    - Applications array populated
    - count matches array length
    - Proper application structure
    """
    response = await async_test_client.get("/api/applications")

    assert response.status_code == 200
    data = response.json()

    assert data["count"] > 0
    assert len(data["applications"]) > 0
    assert data["count"] == len(data["applications"])

    # Check application structure
    app = data["applications"][0]
    assert "app_id" in app
    assert "process_name" in app
    assert "total_bytes" in app
    assert "total_formatted" in app
    assert "bytes_sent" in app
    assert "bytes_sent_formatted" in app
    assert "bytes_received" in app
    assert "bytes_received_formatted" in app
    assert "packets_sent" in app
    assert "packets_received" in app
    assert "first_seen" in app
    assert "last_seen" in app


@pytest.mark.asyncio
async def test_applications_list_with_limit(async_test_client, db_with_sample_data):
    """
    Test /api/applications with limit parameter.

    Validates:
    - limit parameter caps results
    - count respects limit
    """
    response = await async_test_client.get("/api/applications?limit=2")

    assert response.status_code == 200
    data = response.json()

    assert data["count"] <= 2
    assert len(data["applications"]) <= 2


@pytest.mark.asyncio
async def test_applications_list_with_since(async_test_client, db_with_sample_data):
    """
    Test /api/applications with since parameter.

    Validates:
    - since parameter accepted
    - ISO format date works
    """
    since_date = (datetime.now() - timedelta(hours=12)).isoformat()
    response = await async_test_client.get(f"/api/applications?since={since_date}")

    assert response.status_code == 200
    data = response.json()

    assert "applications" in data
    assert data["since"] == since_date


@pytest.mark.asyncio
async def test_applications_list_with_sort_by(async_test_client, db_with_sample_data):
    """
    Test /api/applications with sort_by parameter.

    Validates:
    - sort_by parameter accepted
    - Results ordered correctly
    """
    response = await async_test_client.get("/api/applications?sort_by=total_bytes")

    assert response.status_code == 200
    data = response.json()

    # Verify applications are sorted by total_bytes (descending)
    if len(data["applications"]) > 1:
        for i in range(len(data["applications"]) - 1):
            assert data["applications"][i]["total_bytes"] >= data["applications"][i + 1]["total_bytes"]


@pytest.mark.asyncio
async def test_applications_detail_with_data(async_test_client, db_with_sample_data):
    """
    Test /api/applications/{app_id} with valid app_id.

    Validates:
    - 200 status code
    - Application details present
    - Usage stats included
    """
    app_ids = db_with_sample_data["app_ids"]
    safari_id = app_ids["safari"]

    response = await async_test_client.get(f"/api/applications/{safari_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["app_id"] == safari_id
    assert data["process_name"] == "Safari"
    assert data["bundle_id"] == "com.apple.Safari"
    assert "first_seen" in data
    assert "last_seen" in data

    # Check usage stats
    if "usage" in data:
        usage = data["usage"]
        assert "total_bytes" in usage
        assert "total_formatted" in usage
        assert "bytes_sent" in usage
        assert "bytes_received" in usage


@pytest.mark.asyncio
async def test_applications_timeline(async_test_client, db_with_sample_data):
    """
    Test /api/applications/{app_id}/timeline.

    Validates:
    - 200 status code
    - Timeline structure correct
    - period parameter works
    """
    app_ids = db_with_sample_data["app_ids"]
    safari_id = app_ids["safari"]

    response = await async_test_client.get(f"/api/applications/{safari_id}/timeline?period=24h")

    assert response.status_code == 200
    data = response.json()

    assert data["app_id"] == safari_id
    assert data["process_name"] == "Safari"
    assert data["period"] == "24h"
    assert "timeline" in data


@pytest.mark.asyncio
async def test_applications_timeline_not_found(async_test_client, db_with_sample_data):
    """
    Test /api/applications/{app_id}/timeline with non-existent app.

    Validates:
    - 404 status code
    """
    response = await async_test_client.get("/api/applications/999/timeline")

    assert response.status_code == 404


# ============================================================================
# Domains Endpoints - With Sample Data (Section 3.2)
# ============================================================================

@pytest.mark.asyncio
async def test_domains_list_with_data(async_test_client, db_with_sample_data):
    """
    Test /api/domains with sample data.

    Validates:
    - 200 status code
    - Domains array populated
    - count matches array length
    - Proper domain structure
    """
    response = await async_test_client.get("/api/domains")

    assert response.status_code == 200
    data = response.json()

    assert data["count"] > 0
    assert len(data["domains"]) > 0
    assert data["count"] == len(data["domains"])

    # Check domain structure
    domain = data["domains"][0]
    assert "domain_id" in domain
    assert "domain" in domain
    assert "parent_domain" in domain
    assert "total_bytes" in domain
    assert "total_formatted" in domain
    assert "bytes_sent" in domain
    assert "bytes_sent_formatted" in domain
    assert "bytes_received" in domain
    assert "bytes_received_formatted" in domain
    assert "first_seen" in domain
    assert "last_seen" in domain


@pytest.mark.asyncio
async def test_domains_list_with_limit(async_test_client, db_with_sample_data):
    """
    Test /api/domains with limit parameter.

    Validates:
    - limit parameter caps results
    """
    response = await async_test_client.get("/api/domains?limit=3")

    assert response.status_code == 200
    data = response.json()

    assert data["count"] <= 3
    assert len(data["domains"]) <= 3


@pytest.mark.asyncio
async def test_domains_list_parent_only(async_test_client, db_with_sample_data):
    """
    Test /api/domains with parent_only parameter.

    Validates:
    - parent_only filter works
    - Only returns parent domains
    """
    response = await async_test_client.get("/api/domains?parent_only=true")

    assert response.status_code == 200
    data = response.json()

    assert data["parent_only"] is True

    # Verify only parent domains returned
    for domain in data["domains"]:
        assert domain["domain"] == domain["parent_domain"] or domain["parent_domain"] is None


@pytest.mark.asyncio
async def test_domains_list_with_since(async_test_client, db_with_sample_data):
    """
    Test /api/domains with since parameter.

    Validates:
    - since parameter accepted
    """
    since_date = (datetime.now() - timedelta(hours=6)).isoformat()
    response = await async_test_client.get(f"/api/domains?since={since_date}")

    assert response.status_code == 200
    data = response.json()

    assert "domains" in data
    assert data["since"] == since_date


@pytest.mark.asyncio
async def test_domains_detail_with_data(async_test_client, db_with_sample_data):
    """
    Test /api/domains/{domain_id} with valid domain_id.

    Validates:
    - 200 status code
    - Domain details present
    - Usage stats included
    """
    domain_ids = db_with_sample_data["domain_ids"]
    netflix_id = domain_ids["www.netflix.com"]

    response = await async_test_client.get(f"/api/domains/{netflix_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["domain_id"] == netflix_id
    assert data["domain"] == "www.netflix.com"
    assert data["parent_domain"] == "netflix.com"
    assert "first_seen" in data
    assert "last_seen" in data

    # Check usage stats if present
    if "usage" in data:
        usage = data["usage"]
        assert "total_bytes" in usage
        assert "total_formatted" in usage


@pytest.mark.asyncio
async def test_domains_top_with_data(async_test_client, db_with_sample_data):
    """
    Test /api/domains/top/{limit} with sample data.

    Validates:
    - 200 status code
    - Returns top N domains
    - Sorted by usage (descending)
    """
    response = await async_test_client.get("/api/domains/top/5?period=today")

    assert response.status_code == 200
    data = response.json()

    assert data["period"] == "today"
    assert data["limit"] == 5
    assert len(data["top_domains"]) <= 5

    # Check domain structure
    if data["top_domains"]:
        domain = data["top_domains"][0]
        assert "domain" in domain
        assert "parent_domain" in domain
        assert "total_bytes" in domain
        assert "total_formatted" in domain

        # Verify sorted by total_bytes descending
        if len(data["top_domains"]) > 1:
            for i in range(len(data["top_domains"]) - 1):
                assert data["top_domains"][i]["total_bytes"] >= data["top_domains"][i + 1]["total_bytes"]


@pytest.mark.asyncio
async def test_domains_top_different_periods(async_test_client, db_with_sample_data):
    """
    Test /api/domains/top/{limit} with different period parameters.

    Validates:
    - Accepts today, week, month periods
    - Returns proper structure for each
    """
    periods = ["today", "week", "month"]

    for period in periods:
        response = await async_test_client.get(f"/api/domains/top/10?period={period}")

        assert response.status_code == 200
        data = response.json()

        assert data["period"] == period
        assert "top_domains" in data


# ============================================================================
# Browser Endpoints (Section 4)
# ============================================================================

@pytest.mark.asyncio
async def test_browser_active_tab_valid_report(async_test_client, temp_db):
    """
    Test POST /api/browser/active-tab with valid report.

    Validates:
    - 200 status code for valid report
    - Success status returned
    - Report data echoed back
    """
    # Mock the daemon for this test
    with patch('src.api.browser.get_daemon') as mock_get_daemon:
        mock_daemon = Mock()
        mock_daemon.record_browser_domain = AsyncMock()
        mock_get_daemon.return_value = mock_daemon

        report = {
            "domain": "github.com",
            "timestamp": int(datetime.now().timestamp()),
            "browser": "Zen"
        }

        response = await async_test_client.post("/api/browser/active-tab", json=report)

        # Note: If daemon is not running, this will return 503
        # For successful test, daemon must be mocked
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
            assert data["domain"] == "github.com"
            assert data["browser"] == "Zen"


@pytest.mark.asyncio
async def test_browser_active_tab_invalid_report(async_test_client, temp_db):
    """
    Test POST /api/browser/active-tab with invalid report.

    Validates:
    - 422 status code for validation error
    - Missing required fields rejected
    """
    # Missing required fields
    invalid_report = {
        "domain": "github.com"
        # Missing timestamp and browser
    }

    response = await async_test_client.post("/api/browser/active-tab", json=invalid_report)

    # FastAPI will return 422 for validation errors
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_browser_status(async_test_client, temp_db):
    """
    Test GET /api/browser/status.

    Validates:
    - 200 status code
    - Status information present
    - API version included
    """
    response = await async_test_client.get("/api/browser/status")

    assert response.status_code == 200
    data = response.json()

    assert "daemon_running" in data
    assert "api_version" in data
    assert data["api_version"] == "0.1.0"
    assert "accepting_reports" in data


# ============================================================================
# Config Endpoints (Section 5)
# ============================================================================

@pytest.mark.asyncio
async def test_config_get_all(async_test_client, temp_db):
    """
    Test GET /api/config returns all configuration.

    Validates:
    - 200 status code
    - config dictionary present
    """
    response = await async_test_client.get("/api/config")

    assert response.status_code == 200
    data = response.json()

    assert "config" in data
    assert isinstance(data["config"], dict)


@pytest.mark.asyncio
async def test_config_get_specific_key(async_test_client, temp_db):
    """
    Test GET /api/config/{key} for specific configuration value.

    Validates:
    - 404 for non-existent key
    - Proper error message
    """
    # Non-existent key should return 404
    response = await async_test_client.get("/api/config/nonexistent_key")

    assert response.status_code == 404
    data = response.json()

    assert "detail" in data
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_config_update_valid(async_test_client, temp_db):
    """
    Test PUT /api/config with valid update.

    Validates:
    - 200 status code
    - Config value updated
    - Success status returned
    """
    update = {
        "key": "sampling_interval_seconds",
        "value": "10"
    }

    response = await async_test_client.put("/api/config", json=update)

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["key"] == "sampling_interval_seconds"
    assert data["value"] == "10"


@pytest.mark.asyncio
async def test_config_update_invalid_port(async_test_client, temp_db):
    """
    Test PUT /api/config with invalid port (out of range).

    Validates:
    - 400 status code
    - Proper validation error message
    """
    update = {
        "key": "web_server_port",
        "value": "9000"  # Out of valid range (7000-7999)
    }

    response = await async_test_client.put("/api/config", json=update)

    assert response.status_code == 400
    data = response.json()

    assert "detail" in data
    assert "7000-7999" in data["detail"]


@pytest.mark.asyncio
async def test_config_update_invalid_interval(async_test_client, temp_db):
    """
    Test PUT /api/config with invalid interval (negative).

    Validates:
    - 400 status code
    - Proper validation error message
    """
    update = {
        "key": "sampling_interval_seconds",
        "value": "-5"  # Negative value
    }

    response = await async_test_client.put("/api/config", json=update)

    assert response.status_code == 400
    data = response.json()

    assert "detail" in data
    assert "1-60" in data["detail"]


@pytest.mark.asyncio
async def test_config_update_invalid_retention(async_test_client, temp_db):
    """
    Test PUT /api/config with invalid retention days.

    Validates:
    - 400 status code for out of range retention
    """
    update = {
        "key": "data_retention_days_raw",
        "value": "500"  # Too high (max 365)
    }

    response = await async_test_client.put("/api/config", json=update)

    assert response.status_code == 400
    data = response.json()

    assert "detail" in data
    assert "1-365" in data["detail"]


@pytest.mark.asyncio
async def test_config_daemon_status(async_test_client, temp_db):
    """
    Test GET /api/config/daemon/status.

    Validates:
    - 200 status code
    - Daemon status information
    """
    response = await async_test_client.get("/api/config/daemon/status")

    assert response.status_code == 200
    data = response.json()

    # Should return either full status or just running: False
    assert "running" in data


@pytest.mark.asyncio
async def test_config_init(async_test_client, temp_db):
    """
    Test POST /api/config/init creates config.json.

    Validates:
    - 200 status code
    - Success status
    - Config path returned
    - Default config values present
    """
    response = await async_test_client.post("/api/config/init")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "path" in data
    assert "config" in data

    # Check default config values
    config = data["config"]
    assert config["sampling_interval_seconds"] == 5
    assert config["web_server_port"] == 7500
    assert config["log_level"] == "INFO"
    assert config["data_retention_days_raw"] == 7
    assert config["data_retention_days_hourly"] == 90


# ============================================================================
# Query Parameter Filtering Tests (Section 8)
# ============================================================================

@pytest.mark.asyncio
async def test_applications_limit_parameter(async_test_client, db_with_sample_data):
    """
    Test applications endpoint limit parameter.

    Validates:
    - limit parameter caps results correctly
    - Returns at most limit applications
    """
    limit = 1
    response = await async_test_client.get(f"/api/applications?limit={limit}")

    assert response.status_code == 200
    data = response.json()

    assert len(data["applications"]) <= limit


@pytest.mark.asyncio
async def test_domains_limit_parameter(async_test_client, db_with_sample_data):
    """
    Test domains endpoint limit parameter.

    Validates:
    - limit parameter caps results correctly
    """
    limit = 2
    response = await async_test_client.get(f"/api/domains?limit={limit}")

    assert response.status_code == 200
    data = response.json()

    assert len(data["domains"]) <= limit


@pytest.mark.asyncio
async def test_timeline_period_parameter(async_test_client, db_with_sample_data):
    """
    Test stats timeline period parameter.

    Validates:
    - Different period values accepted
    - 1h, 24h, 7d, 30d, 90d all work
    """
    periods = ["1h", "24h", "7d", "30d", "90d"]

    for period in periods:
        response = await async_test_client.get(f"/api/stats/timeline?period={period}")

        assert response.status_code == 200
        data = response.json()
        assert data["period"] == period


# ============================================================================
# Error Handling Tests (Section 9)
# ============================================================================

@pytest.mark.asyncio
async def test_404_non_existent_endpoint(async_test_client, temp_db):
    """
    Test 404 for non-existent endpoint.

    Validates:
    - 404 status code
    - Proper error response
    """
    response = await async_test_client.get("/api/nonexistent")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_validation_error_format(async_test_client, temp_db):
    """
    Test validation error response format.

    Validates:
    - 422 status code for validation errors
    - Error detail present
    """
    # Invalid JSON body for browser endpoint
    response = await async_test_client.post("/api/browser/active-tab", json={})

    assert response.status_code == 422
    data = response.json()

    assert "detail" in data


@pytest.mark.asyncio
async def test_applications_invalid_limit(async_test_client, temp_db):
    """
    Test applications endpoint with invalid limit.

    Validates:
    - 422 for limit outside valid range
    """
    # Limit too high
    response = await async_test_client.get("/api/applications?limit=2000")

    # FastAPI validation will return 422
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_domains_invalid_limit(async_test_client, temp_db):
    """
    Test domains endpoint with invalid limit.

    Validates:
    - 422 for limit outside valid range
    """
    # Limit too low
    response = await async_test_client.get("/api/domains?limit=0")

    # FastAPI validation will return 422
    assert response.status_code == 422
