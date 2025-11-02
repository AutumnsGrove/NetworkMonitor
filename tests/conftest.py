"""
Shared pytest fixtures for NetworkMonitor test suite.

Provides reusable fixtures for database, FastAPI client, mocks, and test data.
"""
import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta, date
from pathlib import Path
import tempfile
import shutil
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, Mock

# Third-party imports
import httpx
from fastapi.testclient import TestClient

# Project imports
from src.db_queries import (
    init_database, insert_application, insert_domain,
    insert_network_sample, insert_browser_domain_sample
)
from src.models import (
    Application, Domain, NetworkSample, BrowserDomainSample
)
from src.webserver import app
from src.utils import round_to_hour


# ============================================================================
# Pytest Configuration
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def temp_db(monkeypatch):
    """
    Create a temporary database for testing.

    Sets up an isolated SQLite database in a temporary directory,
    patches the database path for the test, and cleans up afterwards.
    """
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
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest_asyncio.fixture
async def db_with_sample_data(temp_db):
    """
    Create a database pre-populated with sample network data.

    Provides:
    - 3 applications (Safari, Chrome, Firefox)
    - 5 domains (netflix.com, google.com, github.com, etc.)
    - Network samples spanning the last 24 hours
    - Browser domain samples

    Returns:
        dict: Contains app_ids, domain_ids, and sample metadata
    """
    # Insert applications
    safari = Application(process_name="Safari", bundle_id="com.apple.Safari")
    chrome = Application(process_name="Chrome", bundle_id="com.google.Chrome")
    firefox = Application(process_name="Firefox", bundle_id="org.mozilla.firefox")

    safari_id = await insert_application(safari)
    chrome_id = await insert_application(chrome)
    firefox_id = await insert_application(firefox)

    # Insert domains
    domains_data = [
        ("netflix.com", "netflix.com"),
        ("www.netflix.com", "netflix.com"),
        ("google.com", "google.com"),
        ("api.github.com", "github.com"),
        ("stackoverflow.com", "stackoverflow.com"),
    ]

    domain_ids = {}
    for domain_name, parent_domain in domains_data:
        domain = Domain(domain=domain_name, parent_domain=parent_domain)
        domain_id = await insert_domain(domain)
        domain_ids[domain_name] = domain_id

    # Insert network samples for the last 24 hours
    now = datetime.now()
    sample_ids = []

    # Generate samples every 5 minutes for last 24 hours
    for hours_ago in range(24):
        for minutes in range(0, 60, 5):
            timestamp = now - timedelta(hours=hours_ago, minutes=minutes)

            # Safari sample (heavier usage)
            safari_sample = NetworkSample(
                app_id=safari_id,
                timestamp=timestamp,
                bytes_sent=1024 * 100 * (1 + hours_ago % 3),  # 100-300 KB
                bytes_received=1024 * 500 * (1 + hours_ago % 4),  # 500-2000 KB
                packets_sent=100 + hours_ago * 10,
                packets_received=500 + hours_ago * 20,
                active_connections=5 + hours_ago % 3
            )
            sample_id = await insert_network_sample(safari_sample)
            sample_ids.append(sample_id)

            # Chrome sample (moderate usage)
            if hours_ago < 12:  # Only last 12 hours
                chrome_sample = NetworkSample(
                    app_id=chrome_id,
                    timestamp=timestamp,
                    bytes_sent=1024 * 50,  # 50 KB
                    bytes_received=1024 * 200,  # 200 KB
                    packets_sent=50,
                    packets_received=200,
                    active_connections=3
                )
                await insert_network_sample(chrome_sample)

            # Firefox sample (light usage)
            if hours_ago < 6:  # Only last 6 hours
                firefox_sample = NetworkSample(
                    app_id=firefox_id,
                    timestamp=timestamp,
                    bytes_sent=1024 * 20,  # 20 KB
                    bytes_received=1024 * 100,  # 100 KB
                    packets_sent=20,
                    packets_received=100,
                    active_connections=1
                )
                await insert_network_sample(firefox_sample)

    # Insert browser domain samples
    for hours_ago in range(12):
        for minutes in range(0, 60, 10):
            timestamp = now - timedelta(hours=hours_ago, minutes=minutes)

            # Netflix traffic from Safari
            netflix_sample = BrowserDomainSample(
                domain_id=domain_ids["www.netflix.com"],
                app_id=safari_id,
                timestamp=timestamp,
                bytes_sent=1024 * 50,
                bytes_received=1024 * 1000  # 1 MB (video streaming)
            )
            await insert_browser_domain_sample(netflix_sample)

            # Google traffic from Chrome
            if hours_ago < 8:
                google_sample = BrowserDomainSample(
                    domain_id=domain_ids["google.com"],
                    app_id=chrome_id,
                    timestamp=timestamp,
                    bytes_sent=1024 * 10,
                    bytes_received=1024 * 50
                )
                await insert_browser_domain_sample(google_sample)

    return {
        "app_ids": {
            "safari": safari_id,
            "chrome": chrome_id,
            "firefox": firefox_id,
        },
        "domain_ids": domain_ids,
        "sample_count": len(sample_ids),
        "time_range": {
            "start": now - timedelta(hours=24),
            "end": now,
        }
    }


# ============================================================================
# FastAPI Test Client Fixtures
# ============================================================================

@pytest.fixture
def app_instance():
    """
    Get the FastAPI application instance.

    Returns:
        FastAPI: The application instance for testing
    """
    return app


@pytest.fixture
def test_client(app_instance):
    """
    Synchronous test client for FastAPI endpoints.

    Uses TestClient for synchronous endpoint testing.
    Best for simple endpoint tests that don't require async operations.
    """
    with TestClient(app_instance) as client:
        yield client


@pytest_asyncio.fixture
async def async_test_client(app_instance) -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Async test client for FastAPI endpoints.

    Uses httpx.AsyncClient for async endpoint testing.
    Required for endpoints that use async database operations.

    Usage:
        async def test_endpoint(async_test_client):
            response = await async_test_client.get("/api/stats")
            assert response.status_code == 200
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_instance),
        base_url="http://testserver"
    ) as client:
        yield client


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_lsof_output():
    """
    Mock lsof command output for process mapper testing.

    Returns sample lsof output that includes various process types
    and network connections.
    """
    return """COMMAND     PID   USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
Safari      1234  user   15u  IPv4 0x1234567890      0t0  TCP 192.168.1.100:51234->142.250.185.78:443 (ESTABLISHED)
Safari      1234  user   16u  IPv4 0x1234567891      0t0  TCP 192.168.1.100:51235->54.230.159.123:443 (ESTABLISHED)
Chrome      5678  user   20u  IPv4 0x2345678901      0t0  TCP 192.168.1.100:51300->172.217.14.206:443 (ESTABLISHED)
Firefox     9012  user   25u  IPv4 0x3456789012      0t0  TCP 192.168.1.100:51400->140.82.113.4:443 (ESTABLISHED)
node        3456  user   10u  IPv4 0x4567890123      0t0  TCP *:3000 (LISTEN)
"""


@pytest.fixture
def mock_process_info():
    """
    Mock process information data structure.

    Returns a dictionary of process information similar to what
    the process mapper would return.
    """
    return {
        "Safari": {
            "pid": 1234,
            "bundle_id": "com.apple.Safari",
            "process_name": "Safari",
            "connections": [
                {
                    "local_addr": "192.168.1.100",
                    "local_port": 51234,
                    "remote_addr": "142.250.185.78",
                    "remote_port": 443,
                    "status": "ESTABLISHED"
                },
                {
                    "local_addr": "192.168.1.100",
                    "local_port": 51235,
                    "remote_addr": "54.230.159.123",
                    "remote_port": 443,
                    "status": "ESTABLISHED"
                }
            ]
        },
        "Chrome": {
            "pid": 5678,
            "bundle_id": "com.google.Chrome",
            "process_name": "Chrome",
            "connections": [
                {
                    "local_addr": "192.168.1.100",
                    "local_port": 51300,
                    "remote_addr": "172.217.14.206",
                    "remote_port": 443,
                    "status": "ESTABLISHED"
                }
            ]
        },
        "Firefox": {
            "pid": 9012,
            "bundle_id": "org.mozilla.firefox",
            "process_name": "Firefox",
            "connections": [
                {
                    "local_addr": "192.168.1.100",
                    "local_port": 51400,
                    "remote_addr": "140.82.113.4",
                    "remote_port": 443,
                    "status": "ESTABLISHED"
                }
            ]
        }
    }


@pytest.fixture
def mock_daemon():
    """
    Mock daemon instance for testing daemon-dependent functionality.

    Returns a Mock with common daemon methods.
    For async methods, use AsyncMock separately in tests.
    """
    daemon = Mock()
    daemon.is_running.return_value = True
    daemon.get_status.return_value = {
        "running": True,
        "uptime_seconds": 3600,
        "samples_collected": 720,
        "active_connections": 15,
        "monitored_applications": 5
    }
    # These can be overridden with AsyncMock in individual tests if needed
    daemon.start = AsyncMock()
    daemon.stop = AsyncMock()
    daemon.collect_sample = AsyncMock()
    return daemon


# ============================================================================
# Time Fixtures
# ============================================================================

@pytest.fixture
def fixed_time():
    """
    Fixed timestamp for consistent time-based testing.

    Returns a datetime set to a specific point in time.
    Useful for testing time-dependent logic with predictable results.
    """
    return datetime(2025, 1, 15, 12, 0, 0)


@pytest.fixture
def time_ranges(fixed_time):
    """
    Pre-calculated time ranges for various testing periods.

    Returns:
        dict: Time ranges for common testing scenarios
            - last_hour: 1 hour ago to now
            - last_24h: 24 hours ago to now
            - last_7d: 7 days ago to now
            - last_30d: 30 days ago to now
            - this_week: Start of week to now
            - this_month: Start of month to now
    """
    now = fixed_time
    return {
        "now": now,
        "last_hour": {
            "start": now - timedelta(hours=1),
            "end": now
        },
        "last_24h": {
            "start": now - timedelta(hours=24),
            "end": now
        },
        "last_7d": {
            "start": now - timedelta(days=7),
            "end": now
        },
        "last_30d": {
            "start": now - timedelta(days=30),
            "end": now
        },
        "this_week": {
            "start": now - timedelta(days=now.weekday()),
            "end": now
        },
        "this_month": {
            "start": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            "end": now
        },
        "yesterday": {
            "start": (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
            "end": (now - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
        }
    }


@pytest.fixture
def hour_boundaries(fixed_time):
    """
    Hourly timestamp boundaries for aggregation testing.

    Returns a list of datetime objects at exact hour boundaries,
    useful for testing hourly aggregation logic.
    """
    base = round_to_hour(fixed_time)
    return [base - timedelta(hours=i) for i in range(24)]


# ============================================================================
# Sample Data Generators
# ============================================================================

@pytest.fixture
def make_application():
    """
    Factory fixture for creating Application instances.

    Returns a callable that creates Application objects with
    customizable or default values.

    Usage:
        def test_something(make_application):
            app = make_application(process_name="TestApp")
            assert app.process_name == "TestApp"
    """
    def _make_application(
        process_name: str = "TestApp",
        bundle_id: str = None,
        first_seen: datetime = None,
        last_seen: datetime = None
    ) -> Application:
        return Application(
            process_name=process_name,
            bundle_id=bundle_id,
            first_seen=first_seen or datetime.now(),
            last_seen=last_seen or datetime.now()
        )
    return _make_application


@pytest.fixture
def make_domain():
    """
    Factory fixture for creating Domain instances.

    Returns a callable that creates Domain objects with
    customizable or default values.
    """
    def _make_domain(
        domain: str = "example.com",
        parent_domain: str = None,
        first_seen: datetime = None,
        last_seen: datetime = None
    ) -> Domain:
        return Domain(
            domain=domain,
            parent_domain=parent_domain or domain,
            first_seen=first_seen or datetime.now(),
            last_seen=last_seen or datetime.now()
        )
    return _make_domain


@pytest.fixture
def make_network_sample():
    """
    Factory fixture for creating NetworkSample instances.

    Returns a callable that creates NetworkSample objects with
    customizable or default values.
    """
    def _make_network_sample(
        app_id: int = 1,
        timestamp: datetime = None,
        bytes_sent: int = 1024,
        bytes_received: int = 2048,
        packets_sent: int = 10,
        packets_received: int = 20,
        active_connections: int = 5
    ) -> NetworkSample:
        return NetworkSample(
            app_id=app_id,
            timestamp=timestamp or datetime.now(),
            bytes_sent=bytes_sent,
            bytes_received=bytes_received,
            packets_sent=packets_sent,
            packets_received=packets_received,
            active_connections=active_connections
        )
    return _make_network_sample


@pytest.fixture
def make_browser_domain_sample():
    """
    Factory fixture for creating BrowserDomainSample instances.

    Returns a callable that creates BrowserDomainSample objects with
    customizable or default values.
    """
    def _make_browser_domain_sample(
        domain_id: int = 1,
        app_id: int = 1,
        timestamp: datetime = None,
        bytes_sent: int = 512,
        bytes_received: int = 1024
    ) -> BrowserDomainSample:
        return BrowserDomainSample(
            domain_id=domain_id,
            app_id=app_id,
            timestamp=timestamp or datetime.now(),
            bytes_sent=bytes_sent,
            bytes_received=bytes_received
        )
    return _make_browser_domain_sample
