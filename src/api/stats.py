"""
Statistics API endpoints.

Provides current and historical network usage statistics.
"""
from fastapi import APIRouter, Query
from datetime import datetime, timedelta
from typing import Optional

from src.db_queries import get_quick_stats, get_samples_since
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

    # Get samples
    samples = await get_samples_since(since)

    # Format for timeline
    timeline = []
    for sample in samples:
        timeline.append({
            "timestamp": sample.timestamp.isoformat(),
            "bytes_sent": sample.bytes_sent,
            "bytes_received": sample.bytes_received,
            "total_bytes": sample.bytes_sent + sample.bytes_received,
            "packets": sample.packets_sent + sample.packets_received
        })

    return {
        "period": period,
        "since": since.isoformat(),
        "granularity": granularity,
        "data_points": len(timeline),
        "timeline": timeline
    }


@router.get("/stats/summary")
async def get_summary_stats(
    since: Optional[str] = Query(None, description="Start date (ISO format)")
):
    """
    Get summary statistics.

    Args:
        since: Optional start date for statistics

    Returns:
        Summary statistics
    """
    since_dt = datetime.fromisoformat(since) if since else None
    stats = await get_quick_stats()

    # Calculate totals
    total_bytes = stats.total_bytes_today
    avg_daily = total_bytes  # Simplified - would calculate from historical data

    return {
        "total_bytes": total_bytes,
        "total_formatted": format_bytes(total_bytes),
        "avg_daily_bytes": avg_daily,
        "avg_daily_formatted": format_bytes(avg_daily),
        "monitoring_since": stats.monitoring_since.isoformat() if stats.monitoring_since else None,
        "top_application": stats.top_app_today,
        "top_domain": stats.top_domain_today
    }
