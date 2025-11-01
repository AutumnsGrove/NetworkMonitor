"""
Domains API endpoints.

Provides browser domain usage data.
"""
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime
from typing import Optional

from src.db_queries import (
    get_domain_usage_stats, get_domain
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
