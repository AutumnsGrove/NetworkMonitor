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
    format_bytes, format_rate, round_to_hour
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
