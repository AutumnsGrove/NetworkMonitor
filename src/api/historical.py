"""
Historical data API endpoints.
Provides aggregated historical data for heatmaps, trends, and analytics.
"""
from fastapi import APIRouter, Query
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List
import aiosqlite

from src.utils import get_db_path, format_bytes

router = APIRouter()


@router.get("/historical/heatmap")
async def get_hourly_heatmap(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)")
):
    """
    Get hourly usage heatmap data for date range.

    Returns aggregated usage by day of week and hour for heatmap visualization.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Heatmap data: [[hour, day_of_week, bytes], ...]
    """
    db_path = get_db_path()

    async with aiosqlite.connect(db_path) as db:
        # Query hourly aggregates grouped by day of week and hour
        query = """
        SELECT
            CAST(strftime('%w', hour_start) AS INTEGER) as day_of_week,
            CAST(strftime('%H', hour_start) AS INTEGER) as hour,
            SUM(bytes_sent + bytes_received) as total_bytes
        FROM hourly_aggregates
        WHERE DATE(hour_start) BETWEEN ? AND ?
        GROUP BY day_of_week, hour
        ORDER BY day_of_week, hour
        """

        async with db.execute(query, (start_date, end_date)) as cursor:
            rows = await cursor.fetchall()

            # Convert to heatmap format: [[day, hour, bytes], ...]
            heatmap_data = []
            for row in rows:
                day_of_week, hour, total_bytes = row
                heatmap_data.append({
                    "day": day_of_week,  # 0 = Sunday, 6 = Saturday
                    "hour": hour,
                    "bytes": total_bytes or 0
                })

            return {
                "start_date": start_date,
                "end_date": end_date,
                "data": heatmap_data
            }


@router.get("/historical/weekly")
async def get_weekly_comparison(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)")
):
    """
    Get weekly usage comparison (current week vs last week vs average).

    Args:
        start_date: Optional start date, defaults to current week

    Returns:
        Weekly comparison data by day of week
    """
    db_path = get_db_path()

    # Calculate date ranges
    today = date.today()

    # Current week (Monday to Sunday)
    current_week_start = today - timedelta(days=today.weekday())
    current_week_end = current_week_start + timedelta(days=6)

    # Last week
    last_week_start = current_week_start - timedelta(days=7)
    last_week_end = last_week_start + timedelta(days=6)

    # Average (last 4 weeks)
    avg_start = current_week_start - timedelta(days=28)
    avg_end = current_week_start - timedelta(days=1)

    async with aiosqlite.connect(db_path) as db:
        # Query for current week
        query_week = """
        SELECT
            CAST(strftime('%w', hour_start) AS INTEGER) as day_of_week,
            SUM(bytes_sent + bytes_received) as total_bytes
        FROM hourly_aggregates
        WHERE DATE(hour_start) BETWEEN ? AND ?
        GROUP BY day_of_week
        ORDER BY day_of_week
        """

        # Current week
        async with db.execute(query_week, (str(current_week_start), str(current_week_end))) as cursor:
            current_week_data = {row[0]: row[1] or 0 for row in await cursor.fetchall()}

        # Last week
        async with db.execute(query_week, (str(last_week_start), str(last_week_end))) as cursor:
            last_week_data = {row[0]: row[1] or 0 for row in await cursor.fetchall()}

        # Average (divide by 4 weeks)
        async with db.execute(query_week, (str(avg_start), str(avg_end))) as cursor:
            avg_data_raw = await cursor.fetchall()
            avg_data = {}
            for day, total in avg_data_raw:
                avg_data[day] = (total or 0) / 4  # Average over 4 weeks

        # Format for response (ensure all 7 days present)
        result = []
        day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

        for day in range(7):
            result.append({
                "day": day,
                "day_name": day_names[day],
                "current_week": current_week_data.get(day, 0),
                "last_week": last_week_data.get(day, 0),
                "average": avg_data.get(day, 0)
            })

        return {
            "current_week_start": str(current_week_start),
            "current_week_end": str(current_week_end),
            "data": result
        }


@router.get("/historical/monthly")
async def get_monthly_comparison(
    months: int = Query(6, description="Number of months to compare", ge=1, le=12)
):
    """
    Get monthly usage comparison for the last N months.

    Args:
        months: Number of months to include (default 6)

    Returns:
        Monthly comparison data
    """
    db_path = get_db_path()

    # Calculate month ranges
    today = date.today()
    month_data = []

    async with aiosqlite.connect(db_path) as db:
        for i in range(months):
            # Calculate month start/end
            if i == 0:
                # Current month
                month_start = date(today.year, today.month, 1)
                month_end = today
            else:
                # Previous months
                target_month = today.month - i
                target_year = today.year

                # Handle year rollover
                while target_month <= 0:
                    target_month += 12
                    target_year -= 1

                month_start = date(target_year, target_month, 1)

                # Get last day of month
                if target_month == 12:
                    month_end = date(target_year + 1, 1, 1) - timedelta(days=1)
                else:
                    month_end = date(target_year, target_month + 1, 1) - timedelta(days=1)

            # Query total for this month
            query = """
            SELECT SUM(bytes_sent + bytes_received) as total_bytes
            FROM hourly_aggregates
            WHERE DATE(hour_start) BETWEEN ? AND ?
            """

            async with db.execute(query, (str(month_start), str(month_end))) as cursor:
                row = await cursor.fetchone()
                total_bytes = row[0] or 0

            month_data.append({
                "month": month_start.strftime("%Y-%m"),
                "month_name": month_start.strftime("%B %Y"),
                "total_bytes": total_bytes,
                "total_formatted": format_bytes(total_bytes)
            })

    # Reverse to show oldest to newest
    month_data.reverse()

    return {
        "months": months,
        "data": month_data
    }


@router.get("/historical/daily")
async def get_daily_usage(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)")
):
    """
    Get daily usage totals for date range.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Daily usage data
    """
    db_path = get_db_path()

    async with aiosqlite.connect(db_path) as db:
        query = """
        SELECT
            DATE(hour_start) as date,
            SUM(bytes_sent + bytes_received) as total_bytes
        FROM hourly_aggregates
        WHERE DATE(hour_start) BETWEEN ? AND ?
        GROUP BY DATE(hour_start)
        ORDER BY date
        """

        async with db.execute(query, (start_date, end_date)) as cursor:
            rows = await cursor.fetchall()

            daily_data = []
            for row in rows:
                date_str, total_bytes = row
                daily_data.append({
                    "date": date_str,
                    "total_bytes": total_bytes or 0,
                    "total_formatted": format_bytes(total_bytes or 0)
                })

            return {
                "start_date": start_date,
                "end_date": end_date,
                "data": daily_data
            }
