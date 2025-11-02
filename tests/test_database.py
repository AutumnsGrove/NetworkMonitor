"""
Tests for database layer (schema, models, queries).

Uses an in-memory SQLite database for testing.
"""
import pytest
import asyncio
from datetime import datetime, timedelta, date
from pathlib import Path
import tempfile
import os

# Import database functions
from src.db_queries import (
    init_database, insert_application, get_application, list_applications,
    insert_domain, get_domain, get_domain_by_name,
    insert_network_sample, get_samples_since,
    create_hourly_aggregates, create_daily_aggregates,
    cleanup_old_samples, get_app_usage_stats, get_quick_stats,
    get_config, set_config, DB_PATH, NETMONITOR_DIR
)
from src.models import (
    Application, Domain, NetworkSample, HourlyAggregate
)
from src.utils import (
    extract_parent_domain, normalize_domain, get_domain_with_parent,
    format_bytes, format_rate, round_to_hour, round_to_day, get_time_ranges,
    get_hours_to_aggregate, get_days_to_aggregate, format_duration,
    get_netmonitor_dir, get_db_path, get_config_path, get_log_dir,
    get_daemon_log_path, get_webserver_log_path, get_extension_log_path,
    is_valid_port, is_valid_interval, is_valid_retention_days,
    get_process_name_from_path, calculate_bandwidth
)


@pytest.fixture
def temp_db(monkeypatch):
    """Create a temporary database for testing."""
    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp())
    temp_db_path = temp_dir / "test_network_monitor.db"

    # Patch the database paths
    monkeypatch.setattr('src.db_queries.NETMONITOR_DIR', temp_dir)
    monkeypatch.setattr('src.db_queries.DB_PATH', temp_db_path)

    # Initialize database
    init_database()

    yield temp_db_path

    # Cleanup - remove all subdirectories and files
    import shutil
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


# ============================================================================
# Schema and Initialization Tests
# ============================================================================

def test_database_initialization(temp_db):
    """Test that database is initialized with correct schema."""
    assert temp_db.exists()
    assert temp_db.stat().st_mode & 0o777 == 0o600  # Check file permissions


# ============================================================================
# Model Validation Tests
# ============================================================================

def test_application_model_validation():
    """Test Application model validation."""
    # Valid application
    app = Application(process_name="Safari", bundle_id="com.apple.Safari")
    assert app.process_name == "Safari"
    assert app.bundle_id == "com.apple.Safari"

    # Empty process name should raise error
    with pytest.raises(ValueError):
        Application(process_name="", bundle_id="test")


def test_domain_model_validation():
    """Test Domain model validation."""
    # Valid domain
    domain = Domain(domain="netflix.com")
    assert domain.domain == "netflix.com"

    # Domain should be lowercased
    domain2 = Domain(domain="Netflix.COM")
    assert domain2.domain == "netflix.com"

    # Domain with path should raise error
    with pytest.raises(ValueError):
        Domain(domain="netflix.com/browse")


def test_network_sample_validation():
    """Test NetworkSample model validation."""
    # Valid sample
    sample = NetworkSample(app_id=1, bytes_sent=1024, bytes_received=2048)
    assert sample.bytes_sent == 1024
    assert sample.bytes_received == 2048

    # Negative values should raise error
    with pytest.raises(ValueError):
        NetworkSample(app_id=1, bytes_sent=-100)


# ============================================================================
# Application CRUD Tests
# ============================================================================

@pytest.mark.asyncio
async def test_insert_and_get_application(temp_db):
    """Test inserting and retrieving applications."""
    app = Application(process_name="Safari", bundle_id="com.apple.Safari")

    # Insert application
    app_id = await insert_application(app)
    assert app_id > 0

    # Retrieve application
    retrieved = await get_application(app_id)
    assert retrieved is not None
    assert retrieved.process_name == "Safari"
    assert retrieved.bundle_id == "com.apple.Safari"


@pytest.mark.asyncio
async def test_list_applications(temp_db):
    """Test listing all applications."""
    # Insert multiple applications
    apps = [
        Application(process_name="Safari", bundle_id="com.apple.Safari"),
        Application(process_name="Chrome", bundle_id="com.google.Chrome"),
        Application(process_name="Firefox", bundle_id="org.mozilla.firefox"),
    ]

    for app in apps:
        await insert_application(app)

    # List all applications
    all_apps = await list_applications()
    assert len(all_apps) >= 3

    process_names = [app.process_name for app in all_apps]
    assert "Safari" in process_names
    assert "Chrome" in process_names
    assert "Firefox" in process_names


# ============================================================================
# Domain CRUD Tests
# ============================================================================

@pytest.mark.asyncio
async def test_insert_and_get_domain(temp_db):
    """Test inserting and retrieving domains."""
    domain = Domain(domain="netflix.com", parent_domain="netflix.com")

    # Insert domain
    domain_id = await insert_domain(domain)
    assert domain_id > 0

    # Retrieve by ID
    retrieved = await get_domain(domain_id)
    assert retrieved is not None
    assert retrieved.domain == "netflix.com"

    # Retrieve by name
    retrieved2 = await get_domain_by_name("netflix.com")
    assert retrieved2 is not None
    assert retrieved2.domain_id == domain_id


# ============================================================================
# Network Sample Tests
# ============================================================================

@pytest.mark.asyncio
async def test_insert_network_sample(temp_db):
    """Test inserting network samples."""
    # First create an application
    app = Application(process_name="Safari", bundle_id="com.apple.Safari")
    app_id = await insert_application(app)

    # Insert network sample
    sample = NetworkSample(
        app_id=app_id,
        bytes_sent=1024,
        bytes_received=2048,
        packets_sent=10,
        packets_received=20,
        active_connections=5
    )

    sample_id = await insert_network_sample(sample)
    assert sample_id > 0


@pytest.mark.asyncio
async def test_get_samples_since(temp_db):
    """Test retrieving samples since a timestamp."""
    # Create application
    app = Application(process_name="Safari")
    app_id = await insert_application(app)

    # Insert samples at different times
    now = datetime.now()
    samples = [
        NetworkSample(app_id=app_id, timestamp=now - timedelta(hours=2), bytes_sent=100),
        NetworkSample(app_id=app_id, timestamp=now - timedelta(hours=1), bytes_sent=200),
        NetworkSample(app_id=app_id, timestamp=now, bytes_sent=300),
    ]

    for sample in samples:
        await insert_network_sample(sample)

    # Get samples from last 90 minutes
    since = now - timedelta(minutes=90)
    recent = await get_samples_since(since)

    assert len(recent) >= 2  # Should get the last two samples


# ============================================================================
# Aggregation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_hourly_aggregates(temp_db):
    """Test creating hourly aggregates from raw samples."""
    # Create application
    app = Application(process_name="Safari")
    app_id = await insert_application(app)

    # Insert samples for a specific hour
    hour_start = round_to_hour(datetime.now() - timedelta(hours=2))
    samples = [
        NetworkSample(
            app_id=app_id,
            timestamp=hour_start + timedelta(minutes=i*5),
            bytes_sent=100,
            bytes_received=200,
            packets_sent=10,
            packets_received=20
        )
        for i in range(12)  # 12 samples (one hour at 5-minute intervals)
    ]

    for sample in samples:
        await insert_network_sample(sample)

    # Create hourly aggregate
    count = await create_hourly_aggregates(hour_start)
    assert count > 0


@pytest.mark.asyncio
async def test_create_daily_aggregates(temp_db):
    """Test creating daily aggregates from hourly aggregates."""
    # Create application
    app = Application(process_name="Safari")
    app_id = await insert_application(app)

    # Insert samples for a specific day
    day_start = (datetime.now() - timedelta(days=1)).date()
    hour_starts = [
        datetime.combine(day_start, datetime.min.time()) + timedelta(hours=i)
        for i in range(24)
    ]

    # Create samples and hourly aggregates
    for hour_start in hour_starts:
        sample = NetworkSample(
            app_id=app_id,
            timestamp=hour_start,
            bytes_sent=100,
            bytes_received=200
        )
        await insert_network_sample(sample)
        await create_hourly_aggregates(hour_start)

    # Create daily aggregate
    count = await create_daily_aggregates(day_start)
    assert count > 0


# ============================================================================
# Cleanup Tests
# ============================================================================

@pytest.mark.asyncio
async def test_cleanup_old_samples(temp_db):
    """Test cleaning up old samples."""
    # Create application
    app = Application(process_name="Safari")
    app_id = await insert_application(app)

    # Insert old samples (10 days ago)
    old_time = datetime.now() - timedelta(days=10)
    old_sample = NetworkSample(
        app_id=app_id,
        timestamp=old_time,
        bytes_sent=100
    )
    await insert_network_sample(old_sample)

    # Insert recent sample
    recent_sample = NetworkSample(
        app_id=app_id,
        timestamp=datetime.now(),
        bytes_sent=200
    )
    await insert_network_sample(recent_sample)

    # Clean up samples older than 7 days
    deleted = await cleanup_old_samples(retention_days=7)
    assert deleted >= 1  # Should delete at least the old sample


# ============================================================================
# Statistics Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_app_usage_stats(temp_db):
    """Test getting application usage statistics."""
    # Create applications
    app1 = Application(process_name="Safari")
    app1_id = await insert_application(app1)

    app2 = Application(process_name="Chrome")
    app2_id = await insert_application(app2)

    # Insert samples
    await insert_network_sample(NetworkSample(app_id=app1_id, bytes_sent=1000, bytes_received=2000))
    await insert_network_sample(NetworkSample(app_id=app2_id, bytes_sent=500, bytes_received=1000))

    # Get stats
    stats = await get_app_usage_stats()
    assert len(stats) >= 2

    # Safari should have more total bytes
    safari_stats = next((s for s in stats if s.process_name == "Safari"), None)
    assert safari_stats is not None
    assert safari_stats.total_bytes == 3000


@pytest.mark.asyncio
async def test_get_quick_stats(temp_db):
    """Test getting quick statistics."""
    # Create application and samples
    app = Application(process_name="Safari")
    app_id = await insert_application(app)

    await insert_network_sample(NetworkSample(
        app_id=app_id,
        timestamp=datetime.now(),
        bytes_sent=1000,
        bytes_received=2000
    ))

    # Get quick stats
    stats = await get_quick_stats()
    assert stats is not None
    assert stats.total_bytes_today >= 3000


# ============================================================================
# Config Tests
# ============================================================================

@pytest.mark.asyncio
async def test_config_operations(temp_db):
    """Test configuration get/set operations."""
    # Set a config value
    await set_config("test_key", "test_value")

    # Get the config value
    value = await get_config("test_key")
    assert value == "test_value"

    # Update config value
    await set_config("test_key", "updated_value")
    value = await get_config("test_key")
    assert value == "updated_value"


# ============================================================================
# Utility Function Tests
# ============================================================================

def test_extract_parent_domain():
    """Test parent domain extraction."""
    assert extract_parent_domain("api.netflix.com") == "netflix.com"
    assert extract_parent_domain("www.example.co.uk") == "example.co.uk"
    assert extract_parent_domain("netflix.com") == "netflix.com"
    assert extract_parent_domain("localhost") == "localhost"
    assert extract_parent_domain("192.168.1.1") == "192.168.1.1"


def test_normalize_domain():
    """Test domain normalization."""
    assert normalize_domain("https://api.netflix.com/v1/users") == "api.netflix.com"
    assert normalize_domain("HTTP://EXAMPLE.COM:8080/path") == "example.com"
    assert normalize_domain("  example.com  ") == "example.com"


def test_get_domain_with_parent():
    """Test getting domain and parent together."""
    domain, parent = get_domain_with_parent("https://api.netflix.com/browse")
    assert domain == "api.netflix.com"
    assert parent == "netflix.com"


def test_format_bytes():
    """Test byte formatting."""
    assert format_bytes(0) == "0 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1536) == "1.5 KB"
    assert format_bytes(1048576) == "1.0 MB"
    assert format_bytes(1073741824) == "1.0 GB"


def test_format_rate():
    """Test data rate formatting."""
    assert format_rate(1024) == "1.0 KB/s"
    assert format_rate(1048576) == "1.0 MB/s"


# ============================================================================
# Time Utility Tests
# ============================================================================

def test_round_to_hour():
    """Test rounding datetime down to hour start."""
    dt = datetime(2025, 11, 1, 14, 35, 42, 123456)
    rounded = round_to_hour(dt)
    assert rounded == datetime(2025, 11, 1, 14, 0, 0, 0)

    # Test already at hour start
    dt_hour = datetime(2025, 11, 1, 14, 0, 0, 0)
    rounded_hour = round_to_hour(dt_hour)
    assert rounded_hour == dt_hour


def test_round_to_day():
    """Test rounding datetime down to day start."""
    dt = datetime(2025, 11, 1, 14, 35, 42, 123456)
    rounded = round_to_day(dt)
    assert rounded == date(2025, 11, 1)

    # Test at midnight
    dt_midnight = datetime(2025, 11, 1, 0, 0, 0, 0)
    rounded_midnight = round_to_day(dt_midnight)
    assert rounded_midnight == date(2025, 11, 1)


def test_get_time_ranges(monkeypatch):
    """Test getting common time ranges for queries."""
    # Mock current time
    mock_now = datetime(2025, 11, 5, 14, 30, 0)  # Tuesday, Nov 5, 2025 at 2:30 PM

    class MockDatetime:
        @staticmethod
        def now():
            return mock_now

        @staticmethod
        def combine(date, time):
            return datetime.combine(date, time)

        min = datetime.min

    monkeypatch.setattr('src.utils.datetime', MockDatetime)

    ranges = get_time_ranges()

    # Verify all expected keys are present
    assert 'last_hour' in ranges
    assert 'today' in ranges
    assert 'yesterday' in ranges
    assert 'last_24h' in ranges
    assert 'last_7d' in ranges
    assert 'last_30d' in ranges
    assert 'this_week' in ranges
    assert 'this_month' in ranges

    # Verify calculations
    assert ranges['last_hour'] == datetime(2025, 11, 5, 13, 30, 0)
    assert ranges['today'] == datetime(2025, 11, 5, 0, 0, 0)
    assert ranges['yesterday'] == datetime(2025, 11, 4, 0, 0, 0)
    assert ranges['last_24h'] == datetime(2025, 11, 4, 14, 30, 0)
    assert ranges['last_7d'] == datetime(2025, 10, 29, 14, 30, 0)
    assert ranges['last_30d'] == datetime(2025, 10, 6, 14, 30, 0)
    # Tuesday is weekday 1, so this_week starts on Monday (weekday 0)
    assert ranges['this_week'] == datetime(2025, 11, 3, 0, 0, 0)
    assert ranges['this_month'] == datetime(2025, 11, 1, 0, 0, 0)


def test_get_hours_to_aggregate(monkeypatch):
    """Test getting list of hours to aggregate."""
    # Mock current time
    mock_now = datetime(2025, 11, 5, 14, 35, 42)

    class MockDatetime:
        @staticmethod
        def now():
            return mock_now

    monkeypatch.setattr('src.utils.datetime', MockDatetime)

    hours = get_hours_to_aggregate()

    # Should return 8 hours
    assert len(hours) == 8

    # Should be hours from 13:00 down to 6:00 (1-8 hours ago)
    expected_hours = [
        datetime(2025, 11, 5, 13, 0, 0),  # 1 hour ago
        datetime(2025, 11, 5, 12, 0, 0),  # 2 hours ago
        datetime(2025, 11, 5, 11, 0, 0),  # 3 hours ago
        datetime(2025, 11, 5, 10, 0, 0),  # 4 hours ago
        datetime(2025, 11, 5, 9, 0, 0),   # 5 hours ago
        datetime(2025, 11, 5, 8, 0, 0),   # 6 hours ago
        datetime(2025, 11, 5, 7, 0, 0),   # 7 hours ago
        datetime(2025, 11, 5, 6, 0, 0),   # 8 hours ago
    ]

    assert hours == expected_hours


def test_get_days_to_aggregate(monkeypatch):
    """Test getting list of days to aggregate."""
    # Mock current date
    mock_now = datetime(2025, 11, 5, 14, 35, 42)

    class MockDatetime:
        @staticmethod
        def now():
            return mock_now

    monkeypatch.setattr('src.utils.datetime', MockDatetime)

    days = get_days_to_aggregate()

    # Should return 7 days
    assert len(days) == 7

    # Should be last 7 complete days
    expected_days = [
        date(2025, 11, 4),  # 1 day ago
        date(2025, 11, 3),  # 2 days ago
        date(2025, 11, 2),  # 3 days ago
        date(2025, 11, 1),  # 4 days ago
        date(2025, 10, 31), # 5 days ago
        date(2025, 10, 30), # 6 days ago
        date(2025, 10, 29), # 7 days ago
    ]

    assert days == expected_days


# ============================================================================
# Data Formatting Tests
# ============================================================================

@pytest.mark.parametrize("seconds,expected", [
    (0, "0s"),
    (30, "30s"),
    (59, "59s"),
    (60, "1m"),
    (90, "1m 30s"),
    (150, "2m 30s"),
    (3600, "1h"),
    (3660, "1h 1m"),
    (3665, "1h 1m 5s"),
    (7200, "2h"),
    (7380, "2h 3m"),
    (86400, "1d"),
    (90000, "1d 1h"),
    (90060, "1d 1h 1m"),
    (172800, "2d"),
])
def test_format_duration(seconds, expected):
    """Test duration formatting for various time periods."""
    assert format_duration(seconds) == expected


# ============================================================================
# Path Management Tests
# ============================================================================

def test_get_netmonitor_dir():
    """Test getting ~/.netmonitor directory path."""
    path = get_netmonitor_dir()
    assert path == Path.home() / ".netmonitor"
    assert isinstance(path, Path)


def test_get_db_path():
    """Test getting database file path."""
    path = get_db_path()
    assert path == Path.home() / ".netmonitor" / "network_monitor.db"
    assert isinstance(path, Path)


def test_get_config_path():
    """Test getting config.json file path."""
    path = get_config_path()
    assert path == Path.home() / ".netmonitor" / "config.json"
    assert isinstance(path, Path)


def test_get_log_dir():
    """Test getting logs directory path."""
    path = get_log_dir()
    assert path == Path.home() / ".netmonitor" / "logs"
    assert isinstance(path, Path)


def test_get_daemon_log_path():
    """Test getting daemon log file path."""
    path = get_daemon_log_path()
    assert path == Path.home() / ".netmonitor" / "logs" / "daemon.log"
    assert isinstance(path, Path)


def test_get_webserver_log_path():
    """Test getting web server log file path."""
    path = get_webserver_log_path()
    assert path == Path.home() / ".netmonitor" / "logs" / "webserver.log"
    assert isinstance(path, Path)


def test_get_extension_log_path():
    """Test getting extension log file path."""
    path = get_extension_log_path()
    assert path == Path.home() / ".netmonitor" / "logs" / "extension.log"
    assert isinstance(path, Path)


# ============================================================================
# Validation Tests
# ============================================================================

@pytest.mark.parametrize("port,expected", [
    (7000, True),
    (7500, True),
    (7999, True),
    (6999, False),
    (8000, False),
    (0, False),
    (-1, False),
    (80, False),
    (8080, False),
])
def test_is_valid_port(port, expected):
    """Test port number validation (7000-7999 range)."""
    assert is_valid_port(port) == expected


@pytest.mark.parametrize("interval,expected", [
    (1, True),
    (30, True),
    (60, True),
    (0, False),
    (61, False),
    (-5, False),
    (120, False),
])
def test_is_valid_interval(interval, expected):
    """Test sampling interval validation (1-60 seconds)."""
    assert is_valid_interval(interval) == expected


@pytest.mark.parametrize("days,expected", [
    (1, True),
    (180, True),
    (365, True),
    (0, False),
    (366, False),
    (-10, False),
    (1000, False),
])
def test_is_valid_retention_days(days, expected):
    """Test retention days validation (1-365 days)."""
    assert is_valid_retention_days(days) == expected


# ============================================================================
# Network Utility Tests
# ============================================================================

@pytest.mark.parametrize("path,expected", [
    ("/Applications/Safari.app/Contents/MacOS/Safari", "Safari"),
    ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "Google Chrome"),
    ("/usr/bin/python3", "python3"),
    ("/usr/local/bin/node", "node"),
    ("/System/Library/PrivateFrameworks/SkyLight.framework/Versions/A/Resources/WindowServer", "WindowServer"),
    ("", "unknown"),
    ("/Applications/Test.app", "Test"),
])
def test_get_process_name_from_path(path, expected):
    """Test process name extraction from full path."""
    assert get_process_name_from_path(path) == expected


@pytest.mark.parametrize("bytes_delta,time_delta,expected", [
    (1024, 1.0, 1024.0),
    (2048, 2.0, 1024.0),
    (1024, 0.5, 2048.0),
    (1024, 0, 0.0),
    (1024, -1.0, 0.0),
    (0, 1.0, 0.0),
])
def test_calculate_bandwidth(bytes_delta, time_delta, expected):
    """Test bandwidth calculation."""
    assert calculate_bandwidth(bytes_delta, time_delta) == expected
