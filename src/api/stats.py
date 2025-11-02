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
