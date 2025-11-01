"""
SQL abstraction layer for Network Monitor.

All database operations are abstracted into functions here.
No raw SQL should appear in the main application code.
"""
import aiosqlite
import sqlite3
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from contextlib import asynccontextmanager

from src.models import (
    Application, Domain, NetworkSample, BrowserDomainSample,
    HourlyAggregate, DailyAggregate, ActiveTab, Config,
    AppUsageStats, DomainUsageStats, TimeSeriesPoint, QuickStats
)


# Database path
NETMONITOR_DIR = Path.home() / ".netmonitor"
DB_PATH = NETMONITOR_DIR / "network_monitor.db"
SCHEMA_PATH = Path(__file__).parent.parent / "schema.sql"


def ensure_netmonitor_dir() -> None:
    """Ensure ~/.netmonitor directory exists with proper permissions."""
    NETMONITOR_DIR.mkdir(parents=True, exist_ok=True)
    # Set directory permissions to 700 (owner read/write/execute only)
    NETMONITOR_DIR.chmod(0o700)

    # Create subdirectories
    (NETMONITOR_DIR / "logs").mkdir(exist_ok=True)
    (NETMONITOR_DIR / "tmp").mkdir(exist_ok=True)


def init_database() -> None:
    """
    Initialize database with schema.
    Creates tables if they don't exist.
    Sets file permissions to 600 (owner read/write only).
    """
    ensure_netmonitor_dir()

    # Read schema from SQL file
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

    with open(SCHEMA_PATH, 'r') as f:
        schema_sql = f.read()

    # Create database and execute schema
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()

    # Set database file permissions to 600
    DB_PATH.chmod(0o600)


@asynccontextmanager
async def get_db_connection():
    """Async context manager for database connections."""
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()


# ============================================================================
# Application Operations
# ============================================================================

async def insert_application(app: Application) -> int:
    """Insert a new application or return existing app_id."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO applications (process_name, bundle_id, first_seen, last_seen)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(process_name, bundle_id) DO UPDATE SET
                last_seen = excluded.last_seen
            RETURNING app_id
            """,
            (app.process_name, app.bundle_id, app.first_seen, app.last_seen)
        )
        row = await cursor.fetchone()
        await conn.commit()
        return row[0]


async def get_application(app_id: int) -> Optional[Application]:
    """Get application by ID."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM applications WHERE app_id = ?", (app_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Application(**dict(row))
        return None


async def get_application_by_name(process_name: str, bundle_id: Optional[str] = None) -> Optional[Application]:
    """Get or create application by process name and bundle_id."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM applications WHERE process_name = ? AND bundle_id IS ?",
            (process_name, bundle_id)
        )
        row = await cursor.fetchone()
        if row:
            return Application(**dict(row))
        return None


async def list_applications() -> List[Application]:
    """List all applications."""
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT * FROM applications ORDER BY last_seen DESC")
        rows = await cursor.fetchall()
        return [Application(**dict(row)) for row in rows]


# ============================================================================
# Domain Operations
# ============================================================================

async def insert_domain(domain: Domain) -> int:
    """Insert a new domain or return existing domain_id."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO domains (domain, parent_domain, first_seen, last_seen)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(domain) DO UPDATE SET
                last_seen = excluded.last_seen
            RETURNING domain_id
            """,
            (domain.domain, domain.parent_domain, domain.first_seen, domain.last_seen)
        )
        row = await cursor.fetchone()
        await conn.commit()
        return row[0]


async def get_domain(domain_id: int) -> Optional[Domain]:
    """Get domain by ID."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM domains WHERE domain_id = ?", (domain_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Domain(**dict(row))
        return None


async def get_domain_by_name(domain_name: str) -> Optional[Domain]:
    """Get domain by name."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM domains WHERE domain = ?", (domain_name.lower(),)
        )
        row = await cursor.fetchone()
        if row:
            return Domain(**dict(row))
        return None


# ============================================================================
# Network Sample Operations
# ============================================================================

async def insert_network_sample(sample: NetworkSample) -> int:
    """Insert a network sample."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO network_samples
            (timestamp, app_id, bytes_sent, bytes_received, packets_sent,
             packets_received, active_connections)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (sample.timestamp, sample.app_id, sample.bytes_sent, sample.bytes_received,
             sample.packets_sent, sample.packets_received, sample.active_connections)
        )
        await conn.commit()
        return cursor.lastrowid


async def insert_browser_domain_sample(sample: BrowserDomainSample) -> int:
    """Insert a browser domain sample."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO browser_domain_samples
            (timestamp, domain_id, app_id, bytes_sent, bytes_received)
            VALUES (?, ?, ?, ?, ?)
            """,
            (sample.timestamp, sample.domain_id, sample.app_id,
             sample.bytes_sent, sample.bytes_received)
        )
        await conn.commit()
        return cursor.lastrowid


async def get_samples_since(since: datetime) -> List[NetworkSample]:
    """Get all network samples since a given timestamp."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT * FROM network_samples
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
            """,
            (since,)
        )
        rows = await cursor.fetchall()
        return [NetworkSample(**dict(row)) for row in rows]


# ============================================================================
# Aggregation Operations
# ============================================================================

async def create_hourly_aggregates(hour_start: datetime) -> int:
    """
    Create hourly aggregates from raw samples for the given hour.
    Returns number of aggregates created.
    """
    hour_end = hour_start + timedelta(hours=1)

    async with get_db_connection() as conn:
        # Aggregate network samples by application
        await conn.execute(
            """
            INSERT INTO hourly_aggregates
            (hour_start, app_id, bytes_sent, bytes_received, packets_sent,
             packets_received, max_active_connections, sample_count)
            SELECT
                ? as hour_start,
                app_id,
                SUM(bytes_sent) as bytes_sent,
                SUM(bytes_received) as bytes_received,
                SUM(packets_sent) as packets_sent,
                SUM(packets_received) as packets_received,
                MAX(active_connections) as max_active_connections,
                COUNT(*) as sample_count
            FROM network_samples
            WHERE timestamp >= ? AND timestamp < ?
            GROUP BY app_id
            ON CONFLICT(hour_start, app_id) DO UPDATE SET
                bytes_sent = excluded.bytes_sent,
                bytes_received = excluded.bytes_received,
                packets_sent = excluded.packets_sent,
                packets_received = excluded.packets_received,
                max_active_connections = excluded.max_active_connections,
                sample_count = excluded.sample_count
            """,
            (hour_start, hour_start, hour_end)
        )

        # Aggregate browser domain samples
        await conn.execute(
            """
            INSERT INTO browser_domain_hourly
            (hour_start, domain_id, app_id, bytes_sent, bytes_received, sample_count)
            SELECT
                ? as hour_start,
                domain_id,
                app_id,
                SUM(bytes_sent) as bytes_sent,
                SUM(bytes_received) as bytes_received,
                COUNT(*) as sample_count
            FROM browser_domain_samples
            WHERE timestamp >= ? AND timestamp < ?
            GROUP BY domain_id, app_id
            ON CONFLICT(hour_start, domain_id, app_id) DO UPDATE SET
                bytes_sent = excluded.bytes_sent,
                bytes_received = excluded.bytes_received,
                sample_count = excluded.sample_count
            """,
            (hour_start, hour_start, hour_end)
        )

        await conn.commit()
        return conn.total_changes


async def create_daily_aggregates(day_start: date) -> int:
    """
    Create daily aggregates from hourly aggregates for the given day.
    Returns number of aggregates created.
    """
    day_end = day_start + timedelta(days=1)

    async with get_db_connection() as conn:
        # Aggregate from hourly data
        await conn.execute(
            """
            INSERT INTO daily_aggregates
            (day_start, app_id, bytes_sent, bytes_received, packets_sent,
             packets_received, max_active_connections, sample_count)
            SELECT
                ? as day_start,
                app_id,
                SUM(bytes_sent) as bytes_sent,
                SUM(bytes_received) as bytes_received,
                SUM(packets_sent) as packets_sent,
                SUM(packets_received) as packets_received,
                MAX(max_active_connections) as max_active_connections,
                SUM(sample_count) as sample_count
            FROM hourly_aggregates
            WHERE DATE(hour_start) = ?
            GROUP BY app_id
            ON CONFLICT(day_start, app_id) DO UPDATE SET
                bytes_sent = excluded.bytes_sent,
                bytes_received = excluded.bytes_received,
                packets_sent = excluded.packets_sent,
                packets_received = excluded.packets_received,
                max_active_connections = excluded.max_active_connections,
                sample_count = excluded.sample_count
            """,
            (day_start, day_start)
        )

        # Aggregate browser domain data
        await conn.execute(
            """
            INSERT INTO browser_domain_daily
            (day_start, domain_id, app_id, bytes_sent, bytes_received, sample_count)
            SELECT
                ? as day_start,
                domain_id,
                app_id,
                SUM(bytes_sent) as bytes_sent,
                SUM(bytes_received) as bytes_received,
                SUM(sample_count) as sample_count
            FROM browser_domain_hourly
            WHERE DATE(hour_start) = ?
            GROUP BY domain_id, app_id
            ON CONFLICT(day_start, domain_id, app_id) DO UPDATE SET
                bytes_sent = excluded.bytes_sent,
                bytes_received = excluded.bytes_received,
                sample_count = excluded.sample_count
            """,
            (day_start, day_start)
        )

        await conn.commit()
        return conn.total_changes


# ============================================================================
# Data Retention / Cleanup Operations
# ============================================================================

async def cleanup_old_samples(retention_days: int = 7) -> int:
    """
    Delete raw samples older than retention_days.
    Returns number of records deleted.
    """
    cutoff_date = datetime.now() - timedelta(days=retention_days)

    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "DELETE FROM network_samples WHERE timestamp < ?",
            (cutoff_date,)
        )
        deleted_network = cursor.rowcount

        cursor = await conn.execute(
            "DELETE FROM browser_domain_samples WHERE timestamp < ?",
            (cutoff_date,)
        )
        deleted_browser = cursor.rowcount

        # Log the cleanup
        await conn.execute(
            """
            INSERT INTO retention_log (operation, records_affected, details)
            VALUES (?, ?, ?)
            """,
            ("cleanup_samples", deleted_network + deleted_browser,
             f"Deleted {deleted_network} network samples and {deleted_browser} browser samples older than {retention_days} days")
        )

        await conn.commit()
        return deleted_network + deleted_browser


async def cleanup_old_hourly_aggregates(retention_days: int = 90) -> int:
    """Delete hourly aggregates older than retention_days."""
    cutoff_date = datetime.now() - timedelta(days=retention_days)

    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "DELETE FROM hourly_aggregates WHERE hour_start < ?",
            (cutoff_date,)
        )
        deleted_hourly = cursor.rowcount

        cursor = await conn.execute(
            "DELETE FROM browser_domain_hourly WHERE hour_start < ?",
            (cutoff_date,)
        )
        deleted_browser = cursor.rowcount

        await conn.execute(
            """
            INSERT INTO retention_log (operation, records_affected, details)
            VALUES (?, ?, ?)
            """,
            ("cleanup_hourly", deleted_hourly + deleted_browser,
             f"Deleted {deleted_hourly} hourly aggregates and {deleted_browser} browser hourly older than {retention_days} days")
        )

        await conn.commit()
        return deleted_hourly + deleted_browser


# ============================================================================
# Statistics and Query Operations
# ============================================================================

async def get_app_usage_stats(since: Optional[datetime] = None, limit: int = 100) -> List[AppUsageStats]:
    """Get application usage statistics."""
    since_clause = "AND ns.timestamp >= ?" if since else ""
    params = [since] if since else []
    params.append(limit)

    async with get_db_connection() as conn:
        cursor = await conn.execute(
            f"""
            SELECT
                a.app_id,
                a.process_name,
                SUM(ns.bytes_sent) as total_bytes_sent,
                SUM(ns.bytes_received) as total_bytes_received,
                SUM(ns.bytes_sent + ns.bytes_received) as total_bytes,
                SUM(ns.packets_sent) as total_packets_sent,
                SUM(ns.packets_received) as total_packets_received,
                a.first_seen,
                a.last_seen
            FROM applications a
            LEFT JOIN network_samples ns ON a.app_id = ns.app_id
            WHERE 1=1 {since_clause}
            GROUP BY a.app_id
            ORDER BY total_bytes DESC
            LIMIT ?
            """,
            params
        )
        rows = await cursor.fetchall()
        return [AppUsageStats(**dict(row)) for row in rows]


async def get_domain_usage_stats(since: Optional[datetime] = None, limit: int = 100) -> List[DomainUsageStats]:
    """Get domain usage statistics."""
    since_clause = "AND bds.timestamp >= ?" if since else ""
    params = [since] if since else []
    params.append(limit)

    async with get_db_connection() as conn:
        cursor = await conn.execute(
            f"""
            SELECT
                d.domain_id,
                d.domain,
                d.parent_domain,
                SUM(bds.bytes_sent) as total_bytes_sent,
                SUM(bds.bytes_received) as total_bytes_received,
                SUM(bds.bytes_sent + bds.bytes_received) as total_bytes,
                d.first_seen,
                d.last_seen
            FROM domains d
            LEFT JOIN browser_domain_samples bds ON d.domain_id = bds.domain_id
            WHERE 1=1 {since_clause}
            GROUP BY d.domain_id
            ORDER BY total_bytes DESC
            LIMIT ?
            """,
            params
        )
        rows = await cursor.fetchall()
        return [DomainUsageStats(**dict(row)) for row in rows]


async def get_quick_stats() -> QuickStats:
    """Get quick statistics for menubar and dashboard."""
    now = datetime.now()
    today = now.date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    async with get_db_connection() as conn:
        # Today's total
        cursor = await conn.execute(
            """
            SELECT SUM(bytes_sent + bytes_received) as total
            FROM network_samples
            WHERE DATE(timestamp) = ?
            """,
            (today,)
        )
        row = await cursor.fetchone()
        total_today = row[0] if row[0] else 0

        # This week's total
        cursor = await conn.execute(
            """
            SELECT SUM(bytes_sent + bytes_received) as total
            FROM network_samples
            WHERE DATE(timestamp) >= ?
            """,
            (week_start,)
        )
        row = await cursor.fetchone()
        total_week = row[0] if row[0] else 0

        # This month's total
        cursor = await conn.execute(
            """
            SELECT SUM(bytes_sent + bytes_received) as total
            FROM network_samples
            WHERE DATE(timestamp) >= ?
            """,
            (month_start,)
        )
        row = await cursor.fetchone()
        total_month = row[0] if row[0] else 0

        # Top app today
        cursor = await conn.execute(
            """
            SELECT a.process_name, SUM(ns.bytes_sent + ns.bytes_received) as total
            FROM applications a
            JOIN network_samples ns ON a.app_id = ns.app_id
            WHERE DATE(ns.timestamp) = ?
            GROUP BY a.app_id
            ORDER BY total DESC
            LIMIT 1
            """,
            (today,)
        )
        row = await cursor.fetchone()
        top_app = row[0] if row else None

        # Top domain today
        cursor = await conn.execute(
            """
            SELECT d.domain, SUM(bds.bytes_sent + bds.bytes_received) as total
            FROM domains d
            JOIN browser_domain_samples bds ON d.domain_id = bds.domain_id
            WHERE DATE(bds.timestamp) = ?
            GROUP BY d.domain_id
            ORDER BY total DESC
            LIMIT 1
            """,
            (today,)
        )
        row = await cursor.fetchone()
        top_domain = row[0] if row else None

        # First sample timestamp
        cursor = await conn.execute(
            "SELECT MIN(timestamp) FROM network_samples"
        )
        row = await cursor.fetchone()
        monitoring_since = row[0] if row[0] else None

        return QuickStats(
            total_bytes_today=total_today,
            total_bytes_this_week=total_week,
            total_bytes_this_month=total_month,
            top_app_today=top_app,
            top_domain_today=top_domain,
            active_connections=0,  # Will be updated by daemon
            monitoring_since=monitoring_since
        )


# ============================================================================
# Config Operations
# ============================================================================

async def get_config(key: str) -> Optional[str]:
    """Get configuration value by key."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT value FROM config WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def set_config(key: str, value: str) -> None:
    """Set configuration value."""
    async with get_db_connection() as conn:
        await conn.execute(
            """
            INSERT INTO config (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, value, datetime.now())
        )
        await conn.commit()


async def insert_active_tab(tab: ActiveTab) -> int:
    """Insert active tab record."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO active_tabs (timestamp, domain_id, browser)
            VALUES (?, ?, ?)
            """,
            (tab.timestamp, tab.domain_id, tab.browser)
        )
        await conn.commit()
        return cursor.lastrowid
