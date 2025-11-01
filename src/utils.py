"""
Utility functions for Network Monitor.

Includes domain rollup, timestamp helpers, data formatting,
and file path management.
"""
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional, Tuple
import re


# ============================================================================
# Domain Utilities
# ============================================================================

# Known multi-level TLDs (e.g., .co.uk, .com.au)
MULTI_LEVEL_TLDS = {
    'co.uk', 'com.au', 'co.nz', 'co.za', 'co.jp', 'com.br',
    'co.in', 'com.cn', 'ac.uk', 'gov.uk', 'org.uk'
}


def extract_parent_domain(domain: str) -> str:
    """
    Extract parent domain from subdomain.

    Examples:
        api.netflix.com -> netflix.com
        www.example.co.uk -> example.co.uk
        localhost -> localhost
        192.168.1.1 -> 192.168.1.1 (IP addresses returned as-is)
    """
    if not domain:
        return domain

    domain = domain.lower().strip()

    # Handle IP addresses - return as-is
    if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', domain):
        return domain

    # Handle localhost
    if domain == 'localhost':
        return domain

    parts = domain.split('.')

    # If only 1 or 2 parts, it's already a parent domain
    if len(parts) <= 2:
        return domain

    # Check for multi-level TLD
    if len(parts) >= 3:
        last_two = f"{parts[-2]}.{parts[-1]}"
        if last_two in MULTI_LEVEL_TLDS:
            # Return domain.tld1.tld2 (e.g., example.co.uk)
            if len(parts) >= 3:
                return f"{parts[-3]}.{parts[-2]}.{parts[-1]}"
            return domain

    # Standard case: return last two parts (domain.tld)
    return f"{parts[-2]}.{parts[-1]}"


def normalize_domain(domain: str) -> str:
    """
    Normalize domain name.

    - Convert to lowercase
    - Remove protocol (http://, https://)
    - Remove path, query, fragment
    - Remove port
    - Strip whitespace
    """
    if not domain:
        return domain

    domain = domain.lower().strip()

    # Remove protocol
    domain = re.sub(r'^https?://', '', domain)

    # Remove path, query, fragment
    domain = domain.split('/')[0]
    domain = domain.split('?')[0]
    domain = domain.split('#')[0]

    # Remove port
    domain = domain.split(':')[0]

    return domain


def get_domain_with_parent(url_or_domain: str) -> Tuple[str, str]:
    """
    Extract both domain and parent domain from URL or domain.

    Returns:
        Tuple of (domain, parent_domain)

    Examples:
        "https://api.netflix.com/v1/users" -> ("api.netflix.com", "netflix.com")
        "www.example.co.uk" -> ("www.example.co.uk", "example.co.uk")
    """
    domain = normalize_domain(url_or_domain)
    parent = extract_parent_domain(domain)
    return (domain, parent)


# ============================================================================
# Time Utilities
# ============================================================================

def round_to_hour(dt: datetime) -> datetime:
    """Round datetime down to the start of the hour."""
    return dt.replace(minute=0, second=0, microsecond=0)


def round_to_day(dt: datetime) -> date:
    """Round datetime down to the start of the day."""
    return dt.date()


def get_time_ranges() -> dict:
    """
    Get common time ranges for queries.

    Returns:
        Dictionary with keys: 'last_hour', 'today', 'yesterday',
        'last_24h', 'last_7d', 'last_30d', 'this_week', 'this_month'
    """
    now = datetime.now()
    today = now.date()

    return {
        'last_hour': now - timedelta(hours=1),
        'today': datetime.combine(today, datetime.min.time()),
        'yesterday': datetime.combine(today - timedelta(days=1), datetime.min.time()),
        'last_24h': now - timedelta(hours=24),
        'last_7d': now - timedelta(days=7),
        'last_30d': now - timedelta(days=30),
        'this_week': datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time()),
        'this_month': datetime.combine(today.replace(day=1), datetime.min.time()),
    }


def get_hours_to_aggregate() -> list:
    """
    Get list of hour timestamps that need aggregation.
    Returns hours from 8 hours ago up to the last complete hour.
    """
    now = datetime.now()
    current_hour = round_to_hour(now)
    hours_to_check = []

    # Check last 8 hours for any missing aggregations
    for i in range(1, 9):
        hour = current_hour - timedelta(hours=i)
        hours_to_check.append(hour)

    return hours_to_check


def get_days_to_aggregate() -> list:
    """
    Get list of dates that need daily aggregation.
    Returns last 7 complete days.
    """
    today = datetime.now().date()
    days = []

    for i in range(1, 8):
        day = today - timedelta(days=i)
        days.append(day)

    return days


# ============================================================================
# Data Formatting
# ============================================================================

def format_bytes(bytes_count: int) -> str:
    """
    Format bytes to human-readable string.

    Examples:
        1024 -> "1.0 KB"
        1536 -> "1.5 KB"
        1048576 -> "1.0 MB"
        5368709120 -> "5.0 GB"
    """
    if bytes_count < 0:
        return "0 B"

    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    size = float(bytes_count)
    unit_index = 0

    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1

    # Format with 1 decimal place, unless it's bytes
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.1f} {units[unit_index]}"


def format_rate(bytes_per_second: float) -> str:
    """
    Format data rate to human-readable string.

    Examples:
        1024 -> "1.0 KB/s"
        1048576 -> "1.0 MB/s"
    """
    return f"{format_bytes(int(bytes_per_second))}/s"


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable string.

    Examples:
        90 -> "1m 30s"
        3665 -> "1h 1m 5s"
        86400 -> "1d"
    """
    if seconds < 60:
        return f"{seconds}s"

    minutes = seconds // 60
    seconds = seconds % 60

    if minutes < 60:
        return f"{minutes}m {seconds}s" if seconds > 0 else f"{minutes}m"

    hours = minutes // 60
    minutes = minutes % 60

    if hours < 24:
        parts = [f"{hours}h"]
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0:
            parts.append(f"{seconds}s")
        return " ".join(parts)

    days = hours // 24
    hours = hours % 24

    parts = [f"{days}d"]
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    return " ".join(parts)


# ============================================================================
# Path Management
# ============================================================================

def get_netmonitor_dir() -> Path:
    """Get ~/.netmonitor directory path."""
    return Path.home() / ".netmonitor"


def get_db_path() -> Path:
    """Get database file path."""
    return get_netmonitor_dir() / "network_monitor.db"


def get_config_path() -> Path:
    """Get config.json file path."""
    return get_netmonitor_dir() / "config.json"


def get_log_dir() -> Path:
    """Get logs directory path."""
    return get_netmonitor_dir() / "logs"


def get_daemon_log_path() -> Path:
    """Get daemon log file path."""
    return get_log_dir() / "daemon.log"


def get_webserver_log_path() -> Path:
    """Get web server log file path."""
    return get_log_dir() / "webserver.log"


def get_extension_log_path() -> Path:
    """Get extension log file path."""
    return get_log_dir() / "extension.log"


# ============================================================================
# Validation
# ============================================================================

def is_valid_port(port: int) -> bool:
    """Check if port number is valid (7000-7999 range)."""
    return 7000 <= port <= 7999


def is_valid_interval(interval: int) -> bool:
    """Check if sampling interval is valid (1-60 seconds)."""
    return 1 <= interval <= 60


def is_valid_retention_days(days: int) -> bool:
    """Check if retention days value is valid (1-365 days)."""
    return 1 <= days <= 365


# ============================================================================
# Network Utilities
# ============================================================================

def get_process_name_from_path(path: str) -> str:
    """
    Extract process name from full path.

    Examples:
        "/Applications/Safari.app/Contents/MacOS/Safari" -> "Safari"
        "/usr/bin/python3" -> "python3"
    """
    if not path:
        return "unknown"

    # Get base name
    name = Path(path).name

    # Remove .app extension if present
    if name.endswith('.app'):
        name = name[:-4]

    return name or "unknown"


def calculate_bandwidth(bytes_delta: int, time_delta_seconds: float) -> float:
    """
    Calculate bandwidth in bytes per second.

    Args:
        bytes_delta: Number of bytes transferred
        time_delta_seconds: Time period in seconds

    Returns:
        Bytes per second (float)
    """
    if time_delta_seconds <= 0:
        return 0.0

    return bytes_delta / time_delta_seconds
