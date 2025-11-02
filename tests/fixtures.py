"""
Test fixtures and mock data for NetworkMonitor tests.

This module provides realistic test data constants and helper functions
(NOT pytest fixtures - those are in conftest.py).
"""
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
import random


# =============================================================================
# SAMPLE LSOF OUTPUT
# =============================================================================

SAMPLE_LSOF_OUTPUT = """p1234
cSafari
nTCP *:49152->192.168.1.100:443 (ESTABLISHED)
p1234
cSafari
nTCP *:49153->172.217.14.206:443 (ESTABLISHED)
p5678
cGoogle Chrome Helper
nTCP *:49200->151.101.1.67:443 (ESTABLISHED)
p5678
cGoogle Chrome Helper
nTCP *:49201->104.244.42.193:443 (ESTABLISHED)
p9012
cZen
nTCP *:49300->13.107.246.51:443 (ESTABLISHED)
p9012
cZen
nTCP *:49301->52.109.16.3:443 (ESTABLISHED)
p3456
cPython
nTCP *:49400->192.30.255.113:443 (ESTABLISHED)
p3456
cPython
nTCP localhost:7500 (LISTEN)
p7890
cSpotify
nTCP *:49500->35.186.224.25:443 (ESTABLISHED)
p7890
cSpotify
nUDP *:57621
p2345
cSlack
nTCP *:49600->54.230.159.82:443 (ESTABLISHED)
p2345
cSlack
nTCP *:49601->3.33.243.3:443 (ESTABLISHED)
p6789
cDiscord
nTCP *:49700->162.159.130.233:443 (ESTABLISHED)
p6789
cDiscord
nUDP *:50000
p4567
cmDNSResponder
nUDP *:5353
p8901
cDropbox
nTCP *:49800->162.125.19.131:443 (ESTABLISHED)
p8901
cDropbox
nTCP *:49801->162.125.19.132:443 (ESTABLISHED)
"""

# Sample lsof output with IPv6 connections
SAMPLE_LSOF_OUTPUT_IPV6 = """p1111
cSafari
nTCP [2001:db8::1]:49152->[2001:4860:4860::8888]:443 (ESTABLISHED)
p2222
cChrome
nTCP [::1]:49200->[::1]:8080 (ESTABLISHED)
p3333
cFirefox
nTCP *:49300->[2606:4700::1]:443 (ESTABLISHED)
"""


# =============================================================================
# SAMPLE PROCESSES
# =============================================================================

SAMPLE_PROCESSES: Dict[str, Dict[str, Any]] = {
    "Safari": {
        "process_name": "Safari",
        "bundle_id": "com.apple.Safari",
        "path": "/Applications/Safari.app/Contents/MacOS/Safari",
        "pids": [1234, 1235, 1236],
    },
    "Chrome": {
        "process_name": "Google Chrome Helper",
        "bundle_id": "com.google.Chrome",
        "path": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "pids": [5678, 5679],
    },
    "Zen": {
        "process_name": "Zen",
        "bundle_id": "io.zen.browser",
        "path": "/Applications/Zen Browser.app/Contents/MacOS/zen",
        "pids": [9012, 9013],
    },
    "Python": {
        "process_name": "Python",
        "bundle_id": None,
        "path": "/usr/local/bin/python3.11",
        "pids": [3456],
    },
    "Spotify": {
        "process_name": "Spotify",
        "bundle_id": "com.spotify.client",
        "path": "/Applications/Spotify.app/Contents/MacOS/Spotify",
        "pids": [7890],
    },
    "Slack": {
        "process_name": "Slack",
        "bundle_id": "com.tinyspeck.slackmacgap",
        "path": "/Applications/Slack.app/Contents/MacOS/Slack",
        "pids": [2345],
    },
    "Discord": {
        "process_name": "Discord",
        "bundle_id": "com.hnc.Discord",
        "path": "/Applications/Discord.app/Contents/MacOS/Discord",
        "pids": [6789],
    },
    "mDNSResponder": {
        "process_name": "mDNSResponder",
        "bundle_id": None,
        "path": "/usr/sbin/mDNSResponder",
        "pids": [4567],
    },
    "Dropbox": {
        "process_name": "Dropbox",
        "bundle_id": "com.getdropbox.dropbox",
        "path": "/Applications/Dropbox.app/Contents/MacOS/Dropbox",
        "pids": [8901],
    },
    "Firefox": {
        "process_name": "Firefox",
        "bundle_id": "org.mozilla.firefox",
        "path": "/Applications/Firefox.app/Contents/MacOS/firefox",
        "pids": [11111],
    },
    "VS Code": {
        "process_name": "Code",
        "bundle_id": "com.microsoft.VSCode",
        "path": "/Applications/Visual Studio Code.app/Contents/MacOS/Electron",
        "pids": [22222],
    },
}


# =============================================================================
# SAMPLE DOMAINS
# =============================================================================

SAMPLE_DOMAINS: List[Dict[str, Any]] = [
    # Top-level domains
    {"domain": "netflix.com", "parent_domain": None},
    {"domain": "youtube.com", "parent_domain": None},
    {"domain": "github.com", "parent_domain": None},
    {"domain": "google.com", "parent_domain": None},
    {"domain": "stackoverflow.com", "parent_domain": None},
    {"domain": "reddit.com", "parent_domain": None},
    {"domain": "twitter.com", "parent_domain": None},
    {"domain": "facebook.com", "parent_domain": None},
    {"domain": "linkedin.com", "parent_domain": None},
    {"domain": "amazon.com", "parent_domain": None},
    {"domain": "cloudflare.com", "parent_domain": None},
    {"domain": "slack.com", "parent_domain": None},
    {"domain": "discord.com", "parent_domain": None},
    {"domain": "spotify.com", "parent_domain": None},
    {"domain": "dropbox.com", "parent_domain": None},

    # Subdomains - Netflix
    {"domain": "www.netflix.com", "parent_domain": "netflix.com"},
    {"domain": "api.netflix.com", "parent_domain": "netflix.com"},
    {"domain": "assets.nflxext.com", "parent_domain": "netflix.com"},
    {"domain": "ichnaea.netflix.com", "parent_domain": "netflix.com"},

    # Subdomains - YouTube
    {"domain": "www.youtube.com", "parent_domain": "youtube.com"},
    {"domain": "i.ytimg.com", "parent_domain": "youtube.com"},
    {"domain": "m.youtube.com", "parent_domain": "youtube.com"},
    {"domain": "gaming.youtube.com", "parent_domain": "youtube.com"},

    # Subdomains - GitHub
    {"domain": "api.github.com", "parent_domain": "github.com"},
    {"domain": "raw.githubusercontent.com", "parent_domain": "github.com"},
    {"domain": "gist.github.com", "parent_domain": "github.com"},
    {"domain": "avatars.githubusercontent.com", "parent_domain": "github.com"},

    # Subdomains - Google
    {"domain": "www.google.com", "parent_domain": "google.com"},
    {"domain": "mail.google.com", "parent_domain": "google.com"},
    {"domain": "drive.google.com", "parent_domain": "google.com"},
    {"domain": "docs.google.com", "parent_domain": "google.com"},
    {"domain": "apis.google.com", "parent_domain": "google.com"},

    # Subdomains - AWS/CDN
    {"domain": "s3.amazonaws.com", "parent_domain": "amazon.com"},
    {"domain": "cloudfront.net", "parent_domain": "amazon.com"},
    {"domain": "cdn.cloudflare.net", "parent_domain": "cloudflare.com"},

    # Subdomains - Social
    {"domain": "www.reddit.com", "parent_domain": "reddit.com"},
    {"domain": "old.reddit.com", "parent_domain": "reddit.com"},
    {"domain": "i.redd.it", "parent_domain": "reddit.com"},
    {"domain": "api.twitter.com", "parent_domain": "twitter.com"},
    {"domain": "pbs.twimg.com", "parent_domain": "twitter.com"},
]


# =============================================================================
# SAMPLE APPLICATIONS
# =============================================================================

SAMPLE_APPLICATIONS: List[Dict[str, Any]] = [
    {
        "process_name": "Safari",
        "bundle_id": "com.apple.Safari",
        "first_seen": datetime.now() - timedelta(days=30),
        "last_seen": datetime.now() - timedelta(minutes=5),
    },
    {
        "process_name": "Google Chrome Helper",
        "bundle_id": "com.google.Chrome",
        "first_seen": datetime.now() - timedelta(days=25),
        "last_seen": datetime.now() - timedelta(minutes=10),
    },
    {
        "process_name": "Zen",
        "bundle_id": "io.zen.browser",
        "first_seen": datetime.now() - timedelta(days=15),
        "last_seen": datetime.now() - timedelta(minutes=2),
    },
    {
        "process_name": "Python",
        "bundle_id": None,
        "first_seen": datetime.now() - timedelta(days=20),
        "last_seen": datetime.now() - timedelta(hours=1),
    },
    {
        "process_name": "Spotify",
        "bundle_id": "com.spotify.client",
        "first_seen": datetime.now() - timedelta(days=40),
        "last_seen": datetime.now() - timedelta(hours=3),
    },
    {
        "process_name": "Slack",
        "bundle_id": "com.tinyspeck.slackmacgap",
        "first_seen": datetime.now() - timedelta(days=50),
        "last_seen": datetime.now() - timedelta(minutes=1),
    },
    {
        "process_name": "Discord",
        "bundle_id": "com.hnc.Discord",
        "first_seen": datetime.now() - timedelta(days=35),
        "last_seen": datetime.now() - timedelta(hours=2),
    },
    {
        "process_name": "Dropbox",
        "bundle_id": "com.getdropbox.dropbox",
        "first_seen": datetime.now() - timedelta(days=60),
        "last_seen": datetime.now() - timedelta(minutes=30),
    },
]


# =============================================================================
# SAMPLE NETWORK SAMPLES
# =============================================================================

SAMPLE_NETWORK_SAMPLES: List[Dict[str, Any]] = [
    # Safari - Heavy browsing
    {
        "timestamp": datetime.now() - timedelta(minutes=5),
        "app_id": 1,  # Safari
        "bytes_sent": 524288,      # 512 KB
        "bytes_received": 5242880,  # 5 MB
        "packets_sent": 512,
        "packets_received": 2048,
        "active_connections": 8,
    },
    {
        "timestamp": datetime.now() - timedelta(minutes=10),
        "app_id": 1,
        "bytes_sent": 262144,      # 256 KB
        "bytes_received": 3145728,  # 3 MB
        "packets_sent": 256,
        "packets_received": 1536,
        "active_connections": 6,
    },

    # Chrome - Video streaming
    {
        "timestamp": datetime.now() - timedelta(minutes=3),
        "app_id": 2,  # Chrome
        "bytes_sent": 131072,      # 128 KB
        "bytes_received": 10485760, # 10 MB (streaming)
        "packets_sent": 128,
        "packets_received": 4096,
        "active_connections": 12,
    },
    {
        "timestamp": datetime.now() - timedelta(minutes=8),
        "app_id": 2,
        "bytes_sent": 98304,       # 96 KB
        "bytes_received": 9437184,  # 9 MB
        "packets_sent": 96,
        "packets_received": 3584,
        "active_connections": 10,
    },

    # Zen - Light browsing
    {
        "timestamp": datetime.now() - timedelta(minutes=2),
        "app_id": 3,  # Zen
        "bytes_sent": 65536,       # 64 KB
        "bytes_received": 1048576,  # 1 MB
        "packets_sent": 64,
        "packets_received": 512,
        "active_connections": 4,
    },

    # Python - API calls
    {
        "timestamp": datetime.now() - timedelta(hours=1),
        "app_id": 4,  # Python
        "bytes_sent": 32768,       # 32 KB
        "bytes_received": 262144,   # 256 KB
        "packets_sent": 32,
        "packets_received": 128,
        "active_connections": 2,
    },

    # Spotify - Audio streaming
    {
        "timestamp": datetime.now() - timedelta(hours=3),
        "app_id": 5,  # Spotify
        "bytes_sent": 16384,       # 16 KB
        "bytes_received": 4194304,  # 4 MB
        "packets_sent": 16,
        "packets_received": 1024,
        "active_connections": 3,
    },

    # Slack - Messaging
    {
        "timestamp": datetime.now() - timedelta(minutes=1),
        "app_id": 6,  # Slack
        "bytes_sent": 8192,        # 8 KB
        "bytes_received": 49152,    # 48 KB
        "packets_sent": 8,
        "packets_received": 24,
        "active_connections": 1,
    },

    # Discord - Voice chat
    {
        "timestamp": datetime.now() - timedelta(hours=2),
        "app_id": 7,  # Discord
        "bytes_sent": 2097152,     # 2 MB (upload)
        "bytes_received": 1048576,  # 1 MB
        "packets_sent": 1024,
        "packets_received": 512,
        "active_connections": 5,
    },

    # Dropbox - File sync
    {
        "timestamp": datetime.now() - timedelta(minutes=30),
        "app_id": 8,  # Dropbox
        "bytes_sent": 20971520,    # 20 MB (upload)
        "bytes_received": 524288,   # 512 KB
        "packets_sent": 8192,
        "packets_received": 256,
        "active_connections": 2,
    },
]


# =============================================================================
# SAMPLE CONFIG VALUES
# =============================================================================

SAMPLE_CONFIG_VALUES: Dict[str, str] = {
    "sampling_interval_seconds": "5",
    "data_retention_days_raw": "7",
    "data_retention_days_hourly": "90",
    "web_server_port": "7500",
    "web_server_host": "localhost",
    "enable_browser_tracking": "true",
    "log_level": "INFO",
    "last_cleanup": datetime.now().isoformat(),
    "last_aggregation": datetime.now().isoformat(),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_lsof_line(
    pid: int,
    command: str,
    local_port: int,
    remote_ip: str,
    remote_port: int,
    state: str = "ESTABLISHED",
    protocol: str = "TCP"
) -> str:
    """
    Generate a single lsof output line.

    Args:
        pid: Process ID
        command: Process command name
        local_port: Local port number
        remote_ip: Remote IP address
        remote_port: Remote port number
        state: Connection state (ESTABLISHED, LISTEN, etc.)
        protocol: Protocol (TCP, UDP)

    Returns:
        Formatted lsof output line
    """
    if protocol == "TCP":
        if state == "LISTEN":
            return f"p{pid}\nc{command}\nn{protocol} *:{local_port} ({state})"
        else:
            return f"p{pid}\nc{command}\nn{protocol} *:{local_port}->{remote_ip}:{remote_port} ({state})"
    else:  # UDP
        return f"p{pid}\nc{command}\nn{protocol} *:{local_port}"


def generate_network_sample(
    app_id: int = 1,
    timestamp: Optional[datetime] = None,
    bytes_sent_range: tuple = (1000, 1000000),
    bytes_received_range: tuple = (10000, 10000000),
    connections_range: tuple = (1, 20)
) -> Dict[str, Any]:
    """
    Generate a network sample with random realistic values.

    Args:
        app_id: Application ID
        timestamp: Sample timestamp (defaults to now)
        bytes_sent_range: Min/max bytes sent
        bytes_received_range: Min/max bytes received
        connections_range: Min/max active connections

    Returns:
        Dictionary representing a network sample
    """
    if timestamp is None:
        timestamp = datetime.now()

    bytes_sent = random.randint(*bytes_sent_range)
    bytes_received = random.randint(*bytes_received_range)

    return {
        "timestamp": timestamp,
        "app_id": app_id,
        "bytes_sent": bytes_sent,
        "bytes_received": bytes_received,
        "packets_sent": bytes_sent // 1024,  # Rough estimate
        "packets_received": bytes_received // 1024,
        "active_connections": random.randint(*connections_range),
    }


def generate_hourly_aggregate(
    app_id: int = 1,
    hour_start: Optional[datetime] = None,
    num_samples: int = 720,  # 1 hour = 720 5-second samples
    bytes_sent_per_sample: int = 100000,
    bytes_received_per_sample: int = 1000000
) -> Dict[str, Any]:
    """
    Generate an hourly aggregate record.

    Args:
        app_id: Application ID
        hour_start: Start of hour (defaults to current hour)
        num_samples: Number of samples in this hour
        bytes_sent_per_sample: Average bytes sent per sample
        bytes_received_per_sample: Average bytes received per sample

    Returns:
        Dictionary representing an hourly aggregate
    """
    if hour_start is None:
        hour_start = datetime.now().replace(minute=0, second=0, microsecond=0)

    total_sent = bytes_sent_per_sample * num_samples
    total_received = bytes_received_per_sample * num_samples

    return {
        "hour_start": hour_start,
        "app_id": app_id,
        "bytes_sent": total_sent,
        "bytes_received": total_received,
        "packets_sent": total_sent // 1024,
        "packets_received": total_received // 1024,
        "max_active_connections": random.randint(5, 25),
        "sample_count": num_samples,
    }


def generate_daily_aggregate(
    app_id: int = 1,
    day_start: Optional[date] = None,
    num_samples: int = 17280,  # 1 day = 17,280 5-second samples
    bytes_sent_per_sample: int = 100000,
    bytes_received_per_sample: int = 1000000
) -> Dict[str, Any]:
    """
    Generate a daily aggregate record.

    Args:
        app_id: Application ID
        day_start: Start of day (defaults to today)
        num_samples: Number of samples in this day
        bytes_sent_per_sample: Average bytes sent per sample
        bytes_received_per_sample: Average bytes received per sample

    Returns:
        Dictionary representing a daily aggregate
    """
    if day_start is None:
        day_start = date.today()

    total_sent = bytes_sent_per_sample * num_samples
    total_received = bytes_received_per_sample * num_samples

    return {
        "day_start": day_start,
        "app_id": app_id,
        "bytes_sent": total_sent,
        "bytes_received": total_received,
        "packets_sent": total_sent // 1024,
        "packets_received": total_received // 1024,
        "max_active_connections": random.randint(10, 30),
        "sample_count": num_samples,
    }


def generate_browser_domain_sample(
    domain_id: int = 1,
    app_id: int = 1,
    timestamp: Optional[datetime] = None,
    bytes_sent_range: tuple = (1000, 100000),
    bytes_received_range: tuple = (10000, 5000000)
) -> Dict[str, Any]:
    """
    Generate a browser domain sample.

    Args:
        domain_id: Domain ID
        app_id: Application ID (browser)
        timestamp: Sample timestamp
        bytes_sent_range: Min/max bytes sent
        bytes_received_range: Min/max bytes received

    Returns:
        Dictionary representing a browser domain sample
    """
    if timestamp is None:
        timestamp = datetime.now()

    return {
        "timestamp": timestamp,
        "domain_id": domain_id,
        "app_id": app_id,
        "bytes_sent": random.randint(*bytes_sent_range),
        "bytes_received": random.randint(*bytes_received_range),
    }


def generate_time_series(
    app_id: int = 1,
    start_time: Optional[datetime] = None,
    duration_hours: int = 24,
    interval_minutes: int = 5,
    bytes_sent_range: tuple = (10000, 500000),
    bytes_received_range: tuple = (100000, 5000000)
) -> List[Dict[str, Any]]:
    """
    Generate a time series of network samples.

    Args:
        app_id: Application ID
        start_time: Start time (defaults to 24 hours ago)
        duration_hours: Duration in hours
        interval_minutes: Interval between samples in minutes
        bytes_sent_range: Min/max bytes sent per sample
        bytes_received_range: Min/max bytes received per sample

    Returns:
        List of network sample dictionaries
    """
    if start_time is None:
        start_time = datetime.now() - timedelta(hours=duration_hours)

    samples = []
    current_time = start_time
    end_time = start_time + timedelta(hours=duration_hours)

    while current_time < end_time:
        samples.append(generate_network_sample(
            app_id=app_id,
            timestamp=current_time,
            bytes_sent_range=bytes_sent_range,
            bytes_received_range=bytes_received_range
        ))
        current_time += timedelta(minutes=interval_minutes)

    return samples


def get_sample_process_info(process_name: str) -> Optional[Dict[str, Any]]:
    """
    Get sample process information by process name.

    Args:
        process_name: Name of the process

    Returns:
        Process info dictionary or None if not found
    """
    return SAMPLE_PROCESSES.get(process_name)


def get_sample_domain(domain: str) -> Optional[Dict[str, Any]]:
    """
    Get sample domain information by domain name.

    Args:
        domain: Domain name

    Returns:
        Domain info dictionary or None if not found
    """
    for d in SAMPLE_DOMAINS:
        if d["domain"] == domain:
            return d
    return None
