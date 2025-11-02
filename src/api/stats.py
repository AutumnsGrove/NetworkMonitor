"""
Statistics API endpoints.

Provides current and historical network usage statistics.
"""
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta, date
from typing import Optional

from src.db_queries import get_quick_stats, get_samples_since, get_daily_summary
from src.utils import get_time_ranges, format_bytes


router = APIRouter()


@router.get("/stats")
async def get_stats():
    """
    Get quick statistics.

    Returns current usage stats for today, this week, and this month.
    """
    stats = await get_quick_stats()

    return {
        "today": {
            "total_bytes": stats.total_bytes_today,
            "total_formatted": format_bytes(stats.total_bytes_today),
            "top_app": stats.top_app_today,
            "top_domain": stats.top_domain_today
        },
        "this_week": {
            "total_bytes": stats.total_bytes_this_week,
            "total_formatted": format_bytes(stats.total_bytes_this_week)
        },
        "this_month": {
            "total_bytes": stats.total_bytes_this_month,
            "total_formatted": format_bytes(stats.total_bytes_this_month)
        },
        "current": {
            "active_connections": stats.active_connections,
            "monitoring_since": stats.monitoring_since.isoformat() if stats.monitoring_since else None
        }
    }


@router.get("/stats/timeline")
async def get_timeline_stats(
    period: str = Query("24h", description="Time period: 1h, 24h, 7d, 30d"),
    granularity: str = Query("auto", description="Data granularity: auto, raw, hourly, daily")
):
    """
    Get timeline statistics for charting.

    Args:
        period: Time period to retrieve (1h, 24h, 7d, 30d)
        granularity: Data granularity (auto, raw, hourly, daily)

    Returns:
        Timeline data points for visualization
    """
    # Parse period
    period_map = {
        "1h": timedelta(hours=1),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90)
    }

    if period not in period_map:
        return {"error": f"Invalid period: {period}"}

    since = datetime.now() - period_map[period]

    # Determine bucket size based on period
    bucket_sizes = {
        "1h": timedelta(minutes=1),      # 60 buckets
        "24h": timedelta(minutes=10),    # 144 buckets
        "7d": timedelta(hours=1),        # 168 buckets
        "30d": timedelta(hours=1),       # 720 buckets
        "90d": timedelta(hours=2)        # 1080 buckets
    }
    bucket_size = bucket_sizes.get(period, timedelta(minutes=10))

    # Get samples
    samples = await get_samples_since(since)

    # Aggregate samples into time buckets
    buckets = {}
    for sample in samples:
        # Round timestamp down to nearest bucket
        bucket_time = sample.timestamp.replace(second=0, microsecond=0)

        # Further round based on bucket size
        if bucket_size >= timedelta(hours=1):
            bucket_time = bucket_time.replace(minute=0)
        elif bucket_size >= timedelta(minutes=10):
            bucket_time = bucket_time.replace(minute=(bucket_time.minute // 10) * 10)

        bucket_key = bucket_time.isoformat()

        if bucket_key not in buckets:
            buckets[bucket_key] = {
                "timestamp": bucket_key,
                "bytes_sent": 0,
                "bytes_received": 0,
                "packets_sent": 0,
                "packets_received": 0
            }

        buckets[bucket_key]["bytes_sent"] += sample.bytes_sent
        buckets[bucket_key]["bytes_received"] += sample.bytes_received
        buckets[bucket_key]["packets_sent"] += sample.packets_sent
        buckets[bucket_key]["packets_received"] += sample.packets_received

    # Convert to sorted timeline
    timeline = sorted(buckets.values(), key=lambda x: x["timestamp"])

    # Add total_bytes field
    for point in timeline:
        point["total_bytes"] = point["bytes_sent"] + point["bytes_received"]
        point["packets"] = point["packets_sent"] + point["packets_received"]

    return {
        "period": period,
        "since": since.isoformat(),
        "granularity": f"{int(bucket_size.total_seconds() / 60)}min" if bucket_size < timedelta(hours=1) else f"{int(bucket_size.total_seconds() / 3600)}h",
        "bucket_size_seconds": int(bucket_size.total_seconds()),
        "data_points": len(timeline),
        "timeline": timeline
    }


@router.get("/stats/summary")
async def get_summary_stats(
    start_date: Optional[str] = Query(None, description="Start date (ISO format YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format YYYY-MM-DD)")
):
    """
    Get summary statistics from daily_aggregates table.

    Args:
        start_date: Optional start date (YYYY-MM-DD). Defaults to 30 days ago.
        end_date: Optional end date (YYYY-MM-DD). Defaults to today.

    Returns:
        Summary statistics including total, average, peak, and lowest daily usage
    """
    # Default to last 30 days if not provided
    if end_date:
        try:
            end_dt = date.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
    else:
        end_dt = date.today()

    if start_date:
        try:
            start_dt = date.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    else:
        start_dt = end_dt - timedelta(days=30)

    # Validate date range
    if start_dt > end_dt:
        raise HTTPException(status_code=400, detail="start_date must be before or equal to end_date")

    # Query database for real statistics
    summary = await get_daily_summary(start_dt, end_dt)

    return {
        "start_date": start_dt.isoformat(),
        "end_date": end_dt.isoformat(),
        "total_bytes": summary["total_bytes"],
        "total_formatted": format_bytes(summary["total_bytes"]),
        "avg_daily_bytes": summary["avg_daily_bytes"],
        "avg_daily_formatted": format_bytes(summary["avg_daily_bytes"]),
        "peak_daily_bytes": summary["peak_daily_bytes"],
        "peak_daily_formatted": format_bytes(summary["peak_daily_bytes"]),
        "lowest_daily_bytes": summary["lowest_daily_bytes"],
        "lowest_daily_formatted": format_bytes(summary["lowest_daily_bytes"]),
        "num_days": summary["num_days"]
    }


@router.get("/stats/bandwidth")
async def get_current_bandwidth():
    """
    Get current bandwidth usage (bytes/second).

    Calculates bandwidth from the last 10 seconds of network samples.
    This is a lightweight endpoint optimized for frequent polling.

    Returns:
        Current bandwidth in bytes/second and MB/s
    """
    # Get samples from last 15 seconds to ensure we have 2-3 complete sampling intervals
    since = datetime.now() - timedelta(seconds=15)
    samples = await get_samples_since(since)

    if not samples:
        return {
            "bytes_per_second": 0,
            "mbps": 0.0,
            "time_window_seconds": 10,
            "sample_count": 0
        }

    # Group samples by timestamp (all processes sampled at same time)
    from collections import defaultdict
    samples_by_time = defaultdict(list)
    for sample in samples:
        # Round to nearest second to group samples from same sampling run
        time_key = sample.timestamp.replace(microsecond=0).isoformat()
        samples_by_time[time_key].append(sample)

    # Get the 2 most recent sampling intervals (each is ~5s)
    sorted_times = sorted(samples_by_time.keys(), reverse=True)[:2]

    if not sorted_times:
        return {
            "bytes_per_second": 0,
            "mbps": 0.0,
            "time_window_seconds": 10,
            "sample_count": 0
        }

    # Sum bytes from the 2 most recent intervals (covers ~10 seconds)
    total_bytes = 0
    sample_count = 0
    for time_key in sorted_times:
        for sample in samples_by_time[time_key]:
            total_bytes += sample.bytes_sent + sample.bytes_received
            sample_count += 1

    # Each sample is a 5-second delta, and we have 2 intervals = 10 seconds
    time_window = 10  # seconds
    bytes_per_second = total_bytes / time_window
    mbps = bytes_per_second / (1024 * 1024)

    return {
        "bytes_per_second": int(bytes_per_second),
        "mbps": round(mbps, 2),
        "time_window_seconds": time_window,
        "sample_count": sample_count
    }
