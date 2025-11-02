"""
Domains API endpoints.

Provides browser domain usage data.
"""
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime
from typing import Optional

from src.db_queries import (
    get_domain_usage_stats, get_domain, get_db
)
from src.utils import format_bytes


router = APIRouter()


@router.get("/domains")
async def list_domains(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    since: Optional[str] = Query(None, description="Start date (ISO format)"),
    parent_only: bool = Query(False, description="Show only parent domains")
):
    """
    List domains with network usage.

    Args:
        limit: Maximum number of results
        since: Optional start date for filtering
        parent_only: Show only parent domains (not subdomains)

    Returns:
        List of domains with usage statistics
    """
    since_dt = datetime.fromisoformat(since) if since else None

    # Get domain stats
    domains = await get_domain_usage_stats(since=since_dt, limit=limit)

    # Filter parent domains if requested
    if parent_only:
        domains = [d for d in domains if d.domain == d.parent_domain or not d.parent_domain]

    # Format response
    result = []
    for domain in domains:
        result.append({
            "domain_id": domain.domain_id,
            "domain": domain.domain,
            "parent_domain": domain.parent_domain,
            "browser": domain.browser,
            "total_bytes": domain.total_bytes,
            "total_formatted": format_bytes(domain.total_bytes),
            "bytes_sent": domain.total_bytes_sent,
            "bytes_sent_formatted": format_bytes(domain.total_bytes_sent),
            "bytes_received": domain.total_bytes_received,
            "bytes_received_formatted": format_bytes(domain.total_bytes_received),
            "first_seen": domain.first_seen.isoformat(),
            "last_seen": domain.last_seen.isoformat()
        })

    return {
        "count": len(result),
        "since": since,
        "parent_only": parent_only,
        "domains": result
    }


@router.get("/domains/{domain_id}")
async def get_domain_details(domain_id: int):
    """
    Get detailed information for a specific domain.

    Args:
        domain_id: Domain ID

    Returns:
        Domain details
    """
    domain = await get_domain(domain_id)

    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Get usage stats
    stats = await get_domain_usage_stats(limit=1000)
    domain_stats = next((s for s in stats if s.domain_id == domain_id), None)

    response = {
        "domain_id": domain.domain_id,
        "domain": domain.domain,
        "parent_domain": domain.parent_domain,
        "first_seen": domain.first_seen.isoformat(),
        "last_seen": domain.last_seen.isoformat()
    }

    if domain_stats:
        response["usage"] = {
            "total_bytes": domain_stats.total_bytes,
            "total_formatted": format_bytes(domain_stats.total_bytes),
            "bytes_sent": domain_stats.total_bytes_sent,
            "bytes_received": domain_stats.total_bytes_received
        }

    return response


@router.get("/domains/top/{limit}")
async def get_top_domains(
    limit: int,
    period: str = Query("today", description="Time period: today, week, month")
):
    """
    Get top N domains by usage.

    Args:
        limit: Number of top domains to return
        period: Time period

    Returns:
        Top domains by usage
    """
    # Map period to datetime
    from src.utils import get_time_ranges
    time_ranges = get_time_ranges()

    period_map = {
        "today": time_ranges['today'],
        "week": time_ranges['this_week'],
        "month": time_ranges['this_month']
    }

    since = period_map.get(period, time_ranges['today'])

    # Get domain stats
    domains = await get_domain_usage_stats(since=since, limit=limit)

    result = []
    for domain in domains[:limit]:
        result.append({
            "domain": domain.domain,
            "parent_domain": domain.parent_domain,
            "total_bytes": domain.total_bytes,
            "total_formatted": format_bytes(domain.total_bytes)
        })

    return {
        "period": period,
        "limit": limit,
        "top_domains": result
    }


@router.get("/domains/{domain_id}/timeline")
async def get_domain_timeline(
    domain_id: int,
    period: str = Query("week", description="Time period: day, week, month"),
    granularity: str = Query("hourly", description="Data granularity: hourly, daily")
):
    """
    Get usage timeline for a specific domain.

    Shows hourly or daily usage data over the specified time period.

    Args:
        domain_id: Domain ID
        period: Time period to show (day, week, month)
        granularity: Data granularity (hourly, daily)

    Returns:
        Time series data for domain usage
    """
    from src.utils import get_time_ranges

    # Verify domain exists
    domain = await get_domain(domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Get time range
    time_ranges = get_time_ranges()
    period_map = {
        "day": time_ranges['today'],
        "week": time_ranges['this_week'],
        "month": time_ranges['this_month']
    }

    since = period_map.get(period)
    if not since:
        raise HTTPException(status_code=400, detail=f"Invalid period: {period}")

    # Query based on granularity
    async with get_db() as db:
        if granularity == "hourly":
            query = """
                SELECT
                    timestamp,
                    bytes_sent,
                    bytes_received,
                    (bytes_sent + bytes_received) as total_bytes
                FROM hourly_aggregates
                WHERE domain_id = ?
                    AND timestamp >= ?
                ORDER BY timestamp ASC
            """
        elif granularity == "daily":
            query = """
                SELECT
                    timestamp,
                    bytes_sent,
                    bytes_received,
                    (bytes_sent + bytes_received) as total_bytes
                FROM daily_aggregates
                WHERE domain_id = ?
                    AND timestamp >= ?
                ORDER BY timestamp ASC
            """
        else:
            raise HTTPException(status_code=400, detail=f"Invalid granularity: {granularity}")

        cursor = await db.execute(query, (domain_id, since.isoformat()))
        rows = await cursor.fetchall()

    # Format response
    timeline = []
    for row in rows:
        timeline.append({
            "timestamp": row[0],
            "bytes_sent": row[1],
            "bytes_received": row[2],
            "total_bytes": row[3],
            "total_formatted": format_bytes(row[3])
        })

    return {
        "domain_id": domain_id,
        "domain": domain.domain,
        "period": period,
        "granularity": granularity,
        "since": since.isoformat(),
        "data_points": len(timeline),
        "timeline": timeline
    }
