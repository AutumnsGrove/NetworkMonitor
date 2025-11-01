"""
Applications API endpoints.

Provides application-level network usage data.
"""
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime
from typing import Optional

from src.db_queries import (
    get_app_usage_stats, get_application, list_applications
)
from src.utils import format_bytes, get_time_ranges


router = APIRouter()


@router.get("/applications")
async def list_apps(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    since: Optional[str] = Query(None, description="Start date (ISO format)"),
    sort_by: str = Query("total_bytes", description="Sort field: total_bytes, process_name")
):
    """
    List all applications with network usage.

    Args:
        limit: Maximum number of results
        since: Optional start date for filtering
        sort_by: Field to sort by

    Returns:
        List of applications with usage statistics
    """
    since_dt = datetime.fromisoformat(since) if since else None

    # Get application stats
    apps = await get_app_usage_stats(since=since_dt, limit=limit)

    # Format response
    result = []
    for app in apps:
        result.append({
            "app_id": app.app_id,
            "process_name": app.process_name,
            "total_bytes": app.total_bytes,
            "total_formatted": format_bytes(app.total_bytes),
            "bytes_sent": app.total_bytes_sent,
            "bytes_sent_formatted": format_bytes(app.total_bytes_sent),
            "bytes_received": app.total_bytes_received,
            "bytes_received_formatted": format_bytes(app.total_bytes_received),
            "packets_sent": app.total_packets_sent,
            "packets_received": app.total_packets_received,
            "first_seen": app.first_seen.isoformat(),
            "last_seen": app.last_seen.isoformat()
        })

    return {
        "count": len(result),
        "since": since,
        "applications": result
    }


@router.get("/applications/{app_id}")
async def get_app_details(app_id: int):
    """
    Get detailed information for a specific application.

    Args:
        app_id: Application ID

    Returns:
        Application details
    """
    app = await get_application(app_id)

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Get usage stats for this app
    stats = await get_app_usage_stats(limit=1000)
    app_stats = next((s for s in stats if s.app_id == app_id), None)

    response = {
        "app_id": app.app_id,
        "process_name": app.process_name,
        "bundle_id": app.bundle_id,
        "first_seen": app.first_seen.isoformat(),
        "last_seen": app.last_seen.isoformat()
    }

    if app_stats:
        response["usage"] = {
            "total_bytes": app_stats.total_bytes,
            "total_formatted": format_bytes(app_stats.total_bytes),
            "bytes_sent": app_stats.total_bytes_sent,
            "bytes_received": app_stats.total_bytes_received,
            "packets_sent": app_stats.total_packets_sent,
            "packets_received": app_stats.total_packets_received
        }

    return response


@router.get("/applications/{app_id}/timeline")
async def get_app_timeline(
    app_id: int,
    period: str = Query("24h", description="Time period: 1h, 24h, 7d, 30d")
):
    """
    Get timeline data for a specific application.

    Args:
        app_id: Application ID
        period: Time period

    Returns:
        Timeline data for the application
    """
    app = await get_application(app_id)

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # This would query samples for this specific app
    # Simplified for now
    return {
        "app_id": app_id,
        "process_name": app.process_name,
        "period": period,
        "timeline": []  # Would contain actual timeline data
    }
