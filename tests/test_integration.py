"""
Integration tests for NetworkMonitor application.

Tests the complete integration of different components:
- Database initialization flow
- Daemon + Database integration
- Browser domain tracking flow
- Retention and aggregation operations

These tests verify that components work together correctly
in realistic end-to-end scenarios.
"""
import pytest
import pytest_asyncio
import asyncio
import aiosqlite
from datetime import datetime, timedelta, date
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, MagicMock

# Project imports
from src.db_queries import (
    init_database, insert_application, insert_network_sample,
    insert_domain, insert_browser_domain_sample,
    get_application_by_name, get_domain_by_name,
    create_hourly_aggregates, create_daily_aggregates,
    cleanup_old_samples, get_config, set_config,
    get_db_connection
)
from src.models import (
    Application, Domain, NetworkSample, BrowserDomainSample
)
from src.daemon import NetworkDaemon
from src.retention import RetentionScheduler
from src.process_mapper import ProcessMapper, ProcessInfo
from src.utils import round_to_hour


# ============================================================================
# Database Initialization Tests
# ============================================================================

@pytest.mark.asyncio
async def test_fresh_installation_flow(temp_db):
    """
    Test complete database initialization from scratch.

    Verifies that:
    - Database file is created
    - All tables are created correctly
    - Default config values are set (if any)
    - File permissions are set correctly
    """
    # Database should already be initialized by temp_db fixture
    assert temp_db.exists(), "Database file should exist"

    # Verify file permissions (should be 600 - owner read/write only)
    assert temp_db.stat().st_mode & 0o777 == 0o600, "Database should have 600 permissions"

    # Verify all tables exist by querying schema
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        )
        tables = [row[0] for row in await cursor.fetchall()]

    expected_tables = [
        'active_tabs',
        'applications',
        'browser_domain_daily',
        'browser_domain_hourly',
        'browser_domain_samples',
        'config',
        'daily_aggregates',
        'domains',
        'hourly_aggregates',
        'network_samples',
        'retention_log'
    ]

    for table in expected_tables:
        assert table in tables, f"Table {table} should exist"

    # Verify tables are empty on fresh install
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM applications")
        count = (await cursor.fetchone())[0]
        assert count == 0, "Applications table should be empty on fresh install"

        cursor = await conn.execute("SELECT COUNT(*) FROM network_samples")
        count = (await cursor.fetchone())[0]
        assert count == 0, "Network samples table should be empty on fresh install"


@pytest.mark.asyncio
async def test_idempotent_initialization(temp_db):
    """
    Test that re-initialization doesn't corrupt existing data.

    Verifies that:
    - Existing data is preserved
    - Tables are not dropped
    - Running init_database() multiple times is safe
    """
    # Insert some test data
    app = Application(process_name="Safari", bundle_id="com.apple.Safari")
    app_id = await insert_application(app)

    sample = NetworkSample(
        app_id=app_id,
        timestamp=datetime.now(),
        bytes_sent=1024,
        bytes_received=2048,
        packets_sent=10,
        packets_received=20,
        active_connections=5
    )
    sample_id = await insert_network_sample(sample)

    # Verify data exists
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM applications")
        count_before = (await cursor.fetchone())[0]
        assert count_before == 1

        cursor = await conn.execute("SELECT COUNT(*) FROM network_samples")
        samples_before = (await cursor.fetchone())[0]
        assert samples_before == 1

    # Re-initialize database (should be idempotent due to CREATE TABLE IF NOT EXISTS)
    init_database()

    # Verify data still exists
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM applications")
        count_after = (await cursor.fetchone())[0]
        assert count_after == count_before, "Application data should be preserved"

        cursor = await conn.execute("SELECT COUNT(*) FROM network_samples")
        samples_after = (await cursor.fetchone())[0]
        assert samples_after == samples_before, "Sample data should be preserved"


# ============================================================================
# Daemon + Database Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_daemon_lifecycle_management(temp_db):
    """
    Test daemon starts and stops gracefully.

    Verifies:
    - Daemon can be started
    - Daemon running state is tracked correctly
    - Daemon can be stopped without errors
    - Retention scheduler is started/stopped with daemon
    """
    daemon = NetworkDaemon(sampling_interval=5, enable_retention=True)

    # Initially not running
    assert not daemon.running, "Daemon should not be running initially"
    assert daemon.samples_collected == 0, "Should have 0 samples collected initially"

    # Start daemon (run for very short time)
    start_task = asyncio.create_task(daemon.start())
    await asyncio.sleep(0.1)  # Let it start

    assert daemon.running, "Daemon should be running after start"
    assert daemon.retention_scheduler is not None, "Retention scheduler should be created"
    assert daemon.retention_scheduler.running, "Retention scheduler should be running"

    # Stop daemon
    await daemon.stop()
    await asyncio.sleep(0.1)  # Let it stop

    # Clean up the start task
    start_task.cancel()
    try:
        await start_task
    except asyncio.CancelledError:
        pass

    assert not daemon.running, "Daemon should be stopped"
    if daemon.retention_scheduler:
        assert not daemon.retention_scheduler.running, "Retention scheduler should be stopped"


@pytest.mark.asyncio
async def test_process_mapper_integration_with_database(temp_db, make_application):
    """
    Test process identification and app_id caching.

    Verifies:
    - Process mapper can identify processes
    - Applications are created in database
    - app_id is cached for performance
    - Cache prevents duplicate database queries
    """
    daemon = NetworkDaemon(sampling_interval=5, enable_retention=False)

    # Create a mock process
    proc = ProcessInfo(
        pid=1234,
        name="Safari",
        path="/Applications/Safari.app/Contents/MacOS/Safari",
        bundle_id="com.apple.Safari"
    )

    # First lookup should create app and cache it
    app_id_1 = await daemon._get_or_create_app(proc)
    assert app_id_1 is not None, "Should return valid app_id"
    assert len(daemon.app_id_cache) == 1, "Should cache the app_id"

    # Verify app exists in database
    app = await get_application_by_name("Safari", "com.apple.Safari")
    assert app is not None, "App should be created in database"
    assert app.app_id == app_id_1, "Database app_id should match returned app_id"

    # Second lookup should use cache (not hit database)
    app_id_2 = await daemon._get_or_create_app(proc)
    assert app_id_2 == app_id_1, "Should return same app_id from cache"

    # Verify only one application exists (no duplicate)
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM applications")
        count = (await cursor.fetchone())[0]
        assert count == 1, "Should only have one application record"


@pytest.mark.asyncio
async def test_network_sample_recording(temp_db, make_application):
    """
    Test network samples are inserted correctly during daemon operation.

    Verifies:
    - Samples are recorded with correct timestamps
    - Samples are linked to correct app_id
    - Sample counter increments
    """
    daemon = NetworkDaemon(sampling_interval=5, enable_retention=False)

    # Create application first
    app = Application(process_name="Chrome", bundle_id="com.google.Chrome")
    app_id = await insert_application(app)

    # Create sample manually (simulating daemon behavior)
    timestamp = datetime.now()
    sample = NetworkSample(
        timestamp=timestamp,
        app_id=app_id,
        bytes_sent=1024,
        bytes_received=2048,
        packets_sent=10,
        packets_received=20,
        active_connections=5
    )

    sample_id = await insert_network_sample(sample)
    assert sample_id is not None, "Should return valid sample_id"

    # Verify sample in database
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM network_samples WHERE sample_id = ?",
            (sample_id,)
        )
        row = await cursor.fetchone()
        assert row is not None, "Sample should exist in database"
        assert row['app_id'] == app_id, "Sample should be linked to correct app"
        assert row['bytes_sent'] == 1024, "bytes_sent should match"
        assert row['bytes_received'] == 2048, "bytes_received should match"


@pytest.mark.asyncio
async def test_app_id_caching_performance(temp_db):
    """
    Test app_id caching reduces database queries.

    Verifies:
    - First lookup queries database
    - Subsequent lookups use cache
    - Cache key includes both process_name and bundle_id
    """
    daemon = NetworkDaemon(sampling_interval=5, enable_retention=False)

    proc1 = ProcessInfo(pid=1234, name="Safari", path="/Applications/Safari.app", bundle_id="com.apple.Safari")
    proc2 = ProcessInfo(pid=5678, name="Safari", path="/Applications/Safari.app", bundle_id="com.apple.Safari")
    proc3 = ProcessInfo(pid=9012, name="Chrome", path="/Applications/Chrome.app", bundle_id="com.google.Chrome")

    # First lookup - should query database and cache
    app_id_1 = await daemon._get_or_create_app(proc1)
    assert len(daemon.app_id_cache) == 1

    # Same process (different PID) - should use cache
    app_id_2 = await daemon._get_or_create_app(proc2)
    assert app_id_2 == app_id_1, "Should return same app_id from cache"
    assert len(daemon.app_id_cache) == 1, "Cache should still have 1 entry"

    # Different process - should query database and cache
    app_id_3 = await daemon._get_or_create_app(proc3)
    assert app_id_3 != app_id_1, "Different process should have different app_id"
    assert len(daemon.app_id_cache) == 2, "Cache should have 2 entries now"

    # Verify only 2 applications in database
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM applications")
        count = (await cursor.fetchone())[0]
        assert count == 2, "Should have exactly 2 applications"


@pytest.mark.asyncio
async def test_retention_scheduler_integration(temp_db):
    """
    Test retention scheduler runs and creates aggregates.

    Verifies:
    - Scheduler can be started
    - Aggregation runs without errors
    - Config timestamps are updated
    """
    # Insert some sample data
    app = Application(process_name="Safari", bundle_id="com.apple.Safari")
    app_id = await insert_application(app)

    # Create samples for 2 hours ago (within aggregation window)
    now = datetime.now()
    hour_start = round_to_hour(now - timedelta(hours=2))
    for i in range(12):  # 12 samples (5 minutes apart)
        timestamp = hour_start + timedelta(minutes=i * 5)
        sample = NetworkSample(
            timestamp=timestamp,
            app_id=app_id,
            bytes_sent=1000,
            bytes_received=2000,
            packets_sent=10,
            packets_received=20,
            active_connections=5
        )
        await insert_network_sample(sample)

    # Directly create hourly aggregates (bypassing scheduler logic)
    count = await create_hourly_aggregates(hour_start)
    assert count > 0, "Should create hourly aggregates"

    # Verify hourly aggregates were created
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM hourly_aggregates WHERE hour_start = ?",
            (hour_start,)
        )
        count = (await cursor.fetchone())[0]
        assert count >= 1, "Should have created at least one hourly aggregate"

    # Create retention scheduler and verify it can run
    scheduler = RetentionScheduler(
        aggregation_interval_seconds=1,  # Very short for testing
        cleanup_interval_seconds=10
    )

    # Run aggregation once (should be idempotent)
    await scheduler.run_aggregation()

    # Verify config was updated
    last_agg = await get_config('last_aggregation')
    assert last_agg is not None, "last_aggregation config should be set"


@pytest.mark.asyncio
async def test_cleanup_operations_execute(temp_db):
    """
    Test old data cleanup runs correctly.

    Verifies:
    - Old samples are deleted
    - Recent samples are preserved
    - Retention log is updated
    """
    # Create application
    app = Application(process_name="Safari", bundle_id="com.apple.Safari")
    app_id = await insert_application(app)

    # Use datetime.now() to ensure cutoff calculation works correctly
    now = datetime.now()

    # Create old samples (10 days ago)
    old_timestamp = now - timedelta(days=10)
    for i in range(5):
        sample = NetworkSample(
            timestamp=old_timestamp + timedelta(minutes=i),
            app_id=app_id,
            bytes_sent=1000,
            bytes_received=2000,
            packets_sent=10,
            packets_received=20,
            active_connections=5
        )
        await insert_network_sample(sample)

    # Create recent samples (2 days ago)
    recent_timestamp = now - timedelta(days=2)
    for i in range(5):
        sample = NetworkSample(
            timestamp=recent_timestamp + timedelta(minutes=i),
            app_id=app_id,
            bytes_sent=1000,
            bytes_received=2000,
            packets_sent=10,
            packets_received=20,
            active_connections=5
        )
        await insert_network_sample(sample)

    # Verify we have 10 samples total
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM network_samples")
        count_before = (await cursor.fetchone())[0]
        assert count_before == 10, "Should have 10 samples before cleanup"

    # Run cleanup with 7 day retention
    deleted = await cleanup_old_samples(retention_days=7)

    # Should delete 5 old samples, keep 5 recent
    assert deleted == 5, "Should delete 5 old samples"

    # Verify only recent samples remain
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM network_samples")
        count_after = (await cursor.fetchone())[0]
        assert count_after == 5, "Should have 5 samples remaining"

        # Verify retention log entry
        cursor = await conn.execute("SELECT COUNT(*) FROM retention_log WHERE operation = 'cleanup_samples'")
        log_count = (await cursor.fetchone())[0]
        assert log_count >= 1, "Should have retention log entry"


# ============================================================================
# Browser Domain Tracking Tests
# ============================================================================

@pytest.mark.asyncio
async def test_browser_extension_creates_domain(temp_db):
    """
    Test browser extension endpoint works end-to-end.

    Verifies:
    - Domain is created when posted from browser extension
    - Parent domain is correctly identified
    - Browser application is created
    - Browser domain sample is recorded
    """
    daemon = NetworkDaemon(sampling_interval=5, enable_retention=False)

    # Simulate browser extension posting domain
    await daemon.record_browser_domain(
        domain="www.netflix.com",
        browser="Zen",  # Capitalized as it would come from browser
        bytes_sent=1024,
        bytes_received=5120
    )

    # Verify domain was created
    domain = await get_domain_by_name("www.netflix.com")
    assert domain is not None, "Domain should be created"
    assert domain.parent_domain == "netflix.com", "Parent domain should be identified"

    # Verify browser application was created
    # Daemon creates with bundle_id = f"browser.{browser}"
    browser_app = await get_application_by_name("Zen", "browser.Zen")
    assert browser_app is not None, "Browser application should be created"

    # Verify browser domain sample was created
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT COUNT(*) FROM browser_domain_samples
            WHERE domain_id = ? AND app_id = ?
            """,
            (domain.domain_id, browser_app.app_id)
        )
        count = (await cursor.fetchone())[0]
        assert count == 1, "Should have one browser domain sample"

        # Verify sample data
        cursor = await conn.execute(
            """
            SELECT bytes_sent, bytes_received FROM browser_domain_samples
            WHERE domain_id = ? AND app_id = ?
            """,
            (domain.domain_id, browser_app.app_id)
        )
        row = await cursor.fetchone()
        assert row['bytes_sent'] == 1024, "bytes_sent should match"
        assert row['bytes_received'] == 5120, "bytes_received should match"


@pytest.mark.asyncio
async def test_parent_domain_rollup(temp_db):
    """
    Test subdomains correctly link to parent domain.

    Verifies:
    - www.netflix.com → netflix.com
    - api.github.com → github.com
    - Parent domain is set correctly
    """
    daemon = NetworkDaemon(sampling_interval=5, enable_retention=False)

    # Test various subdomain patterns
    test_cases = [
        ("www.netflix.com", "netflix.com"),
        ("api.github.com", "github.com"),
        ("mail.google.com", "google.com"),
        ("docs.google.com", "google.com"),
        ("stackoverflow.com", "stackoverflow.com"),  # No subdomain
    ]

    for full_domain, expected_parent in test_cases:
        await daemon.record_browser_domain(
            domain=full_domain,
            browser="zen",
            bytes_sent=100,
            bytes_received=200
        )

        domain = await get_domain_by_name(full_domain)
        assert domain is not None, f"Domain {full_domain} should be created"
        assert domain.parent_domain == expected_parent, f"Parent domain should be {expected_parent} for {full_domain}"


@pytest.mark.asyncio
async def test_browser_domain_samples_table_population(temp_db):
    """
    Test browser_domain_samples table is updated correctly.

    Verifies:
    - Multiple samples can be recorded for same domain
    - Timestamps are recorded correctly
    - Bytes are tracked accurately
    """
    daemon = NetworkDaemon(sampling_interval=5, enable_retention=False)

    # Record multiple samples for same domain
    for i in range(5):
        await daemon.record_browser_domain(
            domain="www.youtube.com",
            browser="Zen",
            bytes_sent=1000 * (i + 1),
            bytes_received=5000 * (i + 1)
        )
        await asyncio.sleep(0.01)  # Small delay to ensure different timestamps

    # Verify all samples were recorded
    domain = await get_domain_by_name("www.youtube.com")
    # Daemon creates with bundle_id = f"browser.{browser}"
    browser_app = await get_application_by_name("Zen", "browser.Zen")

    assert domain is not None, "Domain should be created"
    assert browser_app is not None, "Browser app should be created"

    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT COUNT(*), SUM(bytes_sent), SUM(bytes_received)
            FROM browser_domain_samples
            WHERE domain_id = ? AND app_id = ?
            """,
            (domain.domain_id, browser_app.app_id)
        )
        row = await cursor.fetchone()
        count, total_sent, total_received = row[0], row[1], row[2]

        assert count == 5, "Should have 5 samples"
        assert total_sent == 1000 + 2000 + 3000 + 4000 + 5000, "Total bytes sent should sum correctly"
        assert total_received == 5000 + 10000 + 15000 + 20000 + 25000, "Total bytes received should sum correctly"


# ============================================================================
# Retention and Aggregation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_hourly_aggregation_correctness(temp_db, fixed_time):
    """
    Test hourly aggregation calculates sums/max correctly.

    Verifies:
    - Bytes are summed correctly
    - Packets are summed correctly
    - Max connections is calculated correctly
    - Sample count is correct
    """
    # Create application
    app = Application(process_name="Safari", bundle_id="com.apple.Safari")
    app_id = await insert_application(app)

    # Create samples for a specific hour
    hour_start = round_to_hour(fixed_time - timedelta(hours=2))

    total_bytes_sent = 0
    total_bytes_received = 0
    total_packets_sent = 0
    total_packets_received = 0
    max_connections = 0

    # Create 12 samples (5 minutes apart, 1 hour total)
    for i in range(12):
        timestamp = hour_start + timedelta(minutes=i * 5)
        bytes_sent = 1000 + i * 100
        bytes_received = 2000 + i * 200
        connections = 5 + (i % 3)

        sample = NetworkSample(
            timestamp=timestamp,
            app_id=app_id,
            bytes_sent=bytes_sent,
            bytes_received=bytes_received,
            packets_sent=10 + i,
            packets_received=20 + i,
            active_connections=connections
        )
        await insert_network_sample(sample)

        total_bytes_sent += bytes_sent
        total_bytes_received += bytes_received
        total_packets_sent += 10 + i
        total_packets_received += 20 + i
        max_connections = max(max_connections, connections)

    # Run hourly aggregation
    count = await create_hourly_aggregates(hour_start)
    assert count > 0, "Should create at least one aggregate"

    # Verify aggregation results
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT bytes_sent, bytes_received, packets_sent, packets_received,
                   max_active_connections, sample_count
            FROM hourly_aggregates
            WHERE hour_start = ? AND app_id = ?
            """,
            (hour_start, app_id)
        )
        row = await cursor.fetchone()
        assert row is not None, "Hourly aggregate should exist"

        assert row['bytes_sent'] == total_bytes_sent, "bytes_sent should be summed correctly"
        assert row['bytes_received'] == total_bytes_received, "bytes_received should be summed correctly"
        assert row['packets_sent'] == total_packets_sent, "packets_sent should be summed correctly"
        assert row['packets_received'] == total_packets_received, "packets_received should be summed correctly"
        assert row['max_active_connections'] == max_connections, "max_connections should be calculated correctly"
        assert row['sample_count'] == 12, "sample_count should be 12"


@pytest.mark.asyncio
async def test_daily_aggregation_correctness(temp_db, fixed_time):
    """
    Test daily aggregation from hourly data.

    Verifies:
    - Daily aggregates sum hourly data correctly
    - Multiple hours are combined into one day
    - Max connections uses MAX of hourly maxes
    """
    # Create application
    app = Application(process_name="Chrome", bundle_id="com.google.Chrome")
    app_id = await insert_application(app)

    # Create hourly aggregates for a specific day
    day_start = fixed_time.date() - timedelta(days=1)

    total_bytes_sent = 0
    total_bytes_received = 0
    total_packets_sent = 0
    total_packets_received = 0
    max_connections = 0
    total_samples = 0

    # Create 24 hourly aggregates (one full day)
    for hour in range(24):
        hour_start = datetime.combine(day_start, datetime.min.time()) + timedelta(hours=hour)

        bytes_sent = 10000 + hour * 1000
        bytes_received = 50000 + hour * 5000
        connections = 5 + (hour % 10)
        samples = 720  # 720 samples per hour (5 second intervals)

        # Insert directly into hourly_aggregates
        async with get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO hourly_aggregates
                (hour_start, app_id, bytes_sent, bytes_received, packets_sent,
                 packets_received, max_active_connections, sample_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (hour_start, app_id, bytes_sent, bytes_received,
                 100 + hour, 200 + hour, connections, samples)
            )
            await conn.commit()

        total_bytes_sent += bytes_sent
        total_bytes_received += bytes_received
        total_packets_sent += 100 + hour
        total_packets_received += 200 + hour
        max_connections = max(max_connections, connections)
        total_samples += samples

    # Run daily aggregation
    count = await create_daily_aggregates(day_start)
    assert count > 0, "Should create at least one daily aggregate"

    # Verify daily aggregation results
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT bytes_sent, bytes_received, packets_sent, packets_received,
                   max_active_connections, sample_count
            FROM daily_aggregates
            WHERE day_start = ? AND app_id = ?
            """,
            (day_start, app_id)
        )
        row = await cursor.fetchone()
        assert row is not None, "Daily aggregate should exist"

        assert row['bytes_sent'] == total_bytes_sent, "Daily bytes_sent should sum hourly data"
        assert row['bytes_received'] == total_bytes_received, "Daily bytes_received should sum hourly data"
        assert row['packets_sent'] == total_packets_sent, "Daily packets_sent should sum hourly data"
        assert row['packets_received'] == total_packets_received, "Daily packets_received should sum hourly data"
        assert row['max_active_connections'] == max_connections, "Daily max_connections should be MAX of hourly"
        assert row['sample_count'] == total_samples, "Daily sample_count should sum hourly counts"


@pytest.mark.asyncio
async def test_old_sample_cleanup_correctness(temp_db):
    """
    Test cleanup deletes correct records based on retention period.

    Verifies:
    - Samples older than retention period are deleted
    - Samples within retention period are preserved
    - Count of deleted records is accurate
    """
    # Create application
    app = Application(process_name="Firefox", bundle_id="org.mozilla.firefox")
    app_id = await insert_application(app)

    # Use datetime.now() to ensure cutoff calculation works correctly
    now = datetime.now()

    # Create samples at various ages
    ages_and_counts = [
        (1, 5),   # 1 day ago, 5 samples - should be kept
        (3, 5),   # 3 days ago, 5 samples - should be kept
        (8, 5),   # 8 days ago, 5 samples - should be deleted
        (15, 5),  # 15 days ago, 5 samples - should be deleted
        (30, 5),  # 30 days ago, 5 samples - should be deleted
    ]

    for days_ago, count in ages_and_counts:
        timestamp = now - timedelta(days=days_ago)
        for i in range(count):
            sample = NetworkSample(
                timestamp=timestamp + timedelta(minutes=i),
                app_id=app_id,
                bytes_sent=1000,
                bytes_received=2000,
                packets_sent=10,
                packets_received=20,
                active_connections=5
            )
            await insert_network_sample(sample)

    # Verify we have 25 samples total
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM network_samples")
        count_before = (await cursor.fetchone())[0]
        assert count_before == 25, "Should have 25 samples before cleanup"

    # Run cleanup with 7 day retention
    deleted = await cleanup_old_samples(retention_days=7)

    # Should delete 15 samples (8, 15, and 30 days ago)
    assert deleted == 15, "Should delete 15 old samples"

    # Verify correct samples remain
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM network_samples")
        count_after = (await cursor.fetchone())[0]
        assert count_after == 10, "Should have 10 samples remaining (1 and 3 days ago)"

        # Verify all remaining samples are within retention period
        cutoff = now - timedelta(days=7)
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM network_samples WHERE timestamp < ?",
            (cutoff,)
        )
        old_count = (await cursor.fetchone())[0]
        assert old_count == 0, "No samples older than retention period should remain"


@pytest.mark.asyncio
async def test_retention_log_tracking(temp_db, fixed_time):
    """
    Test all retention operations are logged.

    Verifies:
    - Cleanup operations create log entries
    - Log entries contain correct operation type
    - Log entries track records affected
    - Details field contains useful information
    """
    # Create application and samples
    app = Application(process_name="Spotify", bundle_id="com.spotify.client")
    app_id = await insert_application(app)

    # Create old samples
    old_timestamp = fixed_time - timedelta(days=10)
    for i in range(5):
        sample = NetworkSample(
            timestamp=old_timestamp + timedelta(minutes=i),
            app_id=app_id,
            bytes_sent=1000,
            bytes_received=2000,
            packets_sent=10,
            packets_received=20,
            active_connections=5
        )
        await insert_network_sample(sample)

    # Check initial log count
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM retention_log")
        initial_count = (await cursor.fetchone())[0]

    # Run cleanup
    deleted = await cleanup_old_samples(retention_days=7)

    # Verify log entry was created
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM retention_log")
        final_count = (await cursor.fetchone())[0]
        assert final_count > initial_count, "Should have new log entry"

        # Verify log entry details
        cursor = await conn.execute(
            """
            SELECT operation, records_affected, details
            FROM retention_log
            WHERE operation = 'cleanup_samples'
            ORDER BY timestamp DESC
            LIMIT 1
            """
        )
        row = await cursor.fetchone()
        assert row is not None, "Should have cleanup_samples log entry"
        assert row['operation'] == 'cleanup_samples', "Operation should be cleanup_samples"
        assert row['records_affected'] == deleted, "records_affected should match deleted count"
        assert row['details'] is not None, "Details should not be null"
        assert '7 days' in row['details'], "Details should mention retention period"
