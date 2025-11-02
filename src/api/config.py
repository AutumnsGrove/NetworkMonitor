"""
Configuration API endpoints.

Provides runtime configuration management.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import json
from pathlib import Path

from src.db_queries import get_config, set_config
from src.utils import get_config_path, is_valid_port, is_valid_interval, is_valid_retention_days
from src.daemon import get_daemon
from src.config_manager import get_config_manager
from src.retention import aggregate_all_pending, cleanup_all_old_data


router = APIRouter()


class ConfigUpdate(BaseModel):
    """Configuration update request."""
    key: str
    value: str


class ConfigFile(BaseModel):
    """Configuration file structure."""
    sampling_interval_seconds: int = 5
    web_server_port: int = 7500
    log_level: str = "INFO"
    data_retention_days_raw: int = 7
    data_retention_days_hourly: int = 90
    capture_method: str = "packet_sniffing"
    domain_rollup: bool = True
    high_usage_threshold_gb: int = 10
    enable_notifications: bool = False


@router.get("/config")
async def get_all_config():
    """
    Get all configuration values.

    Returns:
        All configuration key-value pairs
    """
    # Get config from database
    config = {}

    keys = [
        'sampling_interval_seconds',
        'data_retention_days_raw',
        'data_retention_days_hourly',
        'last_cleanup',
        'last_aggregation'
    ]

    for key in keys:
        value = await get_config(key)
        if value is not None:
            config[key] = value

    # Also try to read from config.json if it exists
    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            pass

    return {"config": config}


@router.get("/config/{key}")
async def get_config_value(key: str):
    """
    Get a specific configuration value.

    Args:
        key: Configuration key

    Returns:
        Configuration value
    """
    value = await get_config(key)

    if value is None:
        raise HTTPException(status_code=404, detail=f"Configuration key not found: {key}")

    return {"key": key, "value": value}


@router.put("/config")
async def update_config(update: ConfigUpdate):
    """
    Update a configuration value.

    Args:
        update: ConfigUpdate with key and value

    Returns:
        Success confirmation
    """
    # Validate based on key
    if update.key == "web_server_port":
        port = int(update.value)
        if not is_valid_port(port):
            raise HTTPException(status_code=400, detail="Port must be between 7000-7999")

    elif update.key == "sampling_interval_seconds":
        interval = int(update.value)
        if not is_valid_interval(interval):
            raise HTTPException(status_code=400, detail="Interval must be between 1-60 seconds")

    elif update.key in ["data_retention_days_raw", "data_retention_days_hourly"]:
        days = int(update.value)
        if not is_valid_retention_days(days):
            raise HTTPException(status_code=400, detail="Retention days must be between 1-365")

    # Update in database
    await set_config(update.key, update.value)

    # Also update config.json if it exists
    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)

            file_config[update.key] = update.value

            with open(config_path, 'w') as f:
                json.dump(file_config, f, indent=2)
        except Exception as e:
            pass

    return {
        "status": "success",
        "key": update.key,
        "value": update.value
    }


@router.get("/config/daemon/status")
async def get_daemon_status():
    """
    Get daemon status.

    Returns:
        Daemon status information
    """
    daemon = get_daemon()

    if not daemon:
        return {"running": False}

    return daemon.get_status()


@router.post("/config/init")
async def initialize_config():
    """
    Initialize default configuration file.

    Creates ~/.netmonitor/config.json with default values.
    """
    config_path = get_config_path()

    # Create default config
    default_config = ConfigFile()

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write config file
    with open(config_path, 'w') as f:
        json.dump(default_config.model_dump(), f, indent=2)

    return {
        "status": "success",
        "path": str(config_path),
        "config": default_config.model_dump()
    }


@router.get("/config/all")
async def get_all_config_values():
    """
    Get all configuration values from the config manager.

    Returns all config values with their sources (file/database/default).

    Returns:
        Dictionary with all config values and metadata
    """
    config_mgr = get_config_manager()
    config = config_mgr.config

    # Get all config values
    all_values = config_mgr.get_all_config_values()

    # Add source information
    config_with_sources = {}
    for key, value in all_values.items():
        config_with_sources[key] = {
            "value": value,
            "source": config.get_config_source(key)
        }

    return {
        "config": config_with_sources,
        "config_file": str(config_mgr._get_config_path())
    }


@router.post("/config/aggregate")
async def trigger_aggregation():
    """
    Manually trigger data aggregation.

    Aggregates raw samples into hourly data and hourly data into daily aggregates.

    Returns:
        Dictionary with counts of aggregates created
    """
    try:
        result = await aggregate_all_pending()

        return {
            "status": "success",
            "message": "Aggregation completed",
            "hourly_aggregates": result.get('hourly_aggregates', 0),
            "daily_aggregates": result.get('daily_aggregates', 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Aggregation failed: {str(e)}")


@router.post("/config/cleanup")
async def trigger_cleanup():
    """
    Manually trigger cleanup of old data based on retention policies.

    Removes raw samples and hourly aggregates older than configured retention periods.

    Returns:
        Dictionary with counts of records deleted
    """
    try:
        # Get retention policies from config
        raw_retention_str = await get_config('data_retention_days_raw')
        hourly_retention_str = await get_config('data_retention_days_hourly')

        raw_retention = int(raw_retention_str) if raw_retention_str else 7
        hourly_retention = int(hourly_retention_str) if hourly_retention_str else 90

        result = await cleanup_all_old_data(raw_retention, hourly_retention)

        return {
            "status": "success",
            "message": f"Cleanup completed: {result['deleted_samples']} samples, {result['deleted_hourly']} hourly aggregates deleted",
            "deleted_samples": result.get('deleted_samples', 0),
            "deleted_hourly": result.get('deleted_hourly', 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.post("/config/refresh-cache")
async def refresh_cache():
    """
    Clear internal caches (process mapper, domain cache, app cache).

    Forces the system to rebuild caches from fresh data.

    Returns:
        Dictionary with cache clear status
    """
    try:
        daemon = get_daemon()

        if not daemon:
            raise HTTPException(status_code=503, detail="Daemon not running")

        # Clear daemon caches
        daemon.app_id_cache.clear()
        daemon.domain_id_cache.clear()

        # Clear process mapper cache
        if hasattr(daemon, 'process_mapper') and daemon.process_mapper:
            daemon.process_mapper.clear_cache()

        return {
            "status": "success",
            "message": "All caches cleared successfully",
            "caches_cleared": ["app_id_cache", "domain_id_cache", "process_mapper_cache"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache refresh failed: {str(e)}")


@router.get("/export")
async def export_data(
    format: str = "csv",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Export database data to CSV or JSON format.

    Args:
        format: Export format - 'csv' or 'json' (default: csv)
        start_date: Optional start date (ISO format: YYYY-MM-DD)
        end_date: Optional end date (ISO format: YYYY-MM-DD)

    Returns:
        Exported data in requested format
    """
    try:
        import csv
        from io import StringIO
        from datetime import datetime
        from src.db_queries import get_db_connection

        # Validate format
        if format not in ["csv", "json"]:
            raise HTTPException(status_code=400, detail="Format must be 'csv' or 'json'")

        # Parse dates if provided
        where_clause = ""
        params = []

        if start_date or end_date:
            conditions = []
            if start_date:
                try:
                    datetime.fromisoformat(start_date)
                    conditions.append("timestamp >= ?")
                    params.append(start_date)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")

            if end_date:
                try:
                    datetime.fromisoformat(end_date)
                    conditions.append("timestamp <= ?")
                    params.append(end_date)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")

            where_clause = " WHERE " + " AND ".join(conditions)

        # Query data from browser_domain_hourly (includes both app and domain info)
        async with get_db_connection() as db:
            # Adjust where clause to use hour_start instead of timestamp
            adjusted_where = where_clause.replace("timestamp", "h.hour_start") if where_clause else ""

            query = f"""
                SELECT
                    h.hour_start as timestamp,
                    a.process_name as application,
                    d.domain,
                    h.bytes_sent,
                    h.bytes_received,
                    (h.bytes_sent + h.bytes_received) as total_bytes
                FROM browser_domain_hourly h
                LEFT JOIN applications a ON h.app_id = a.app_id
                LEFT JOIN domains d ON h.domain_id = d.domain_id
                {adjusted_where}
                ORDER BY h.hour_start DESC
                LIMIT 10000
            """

            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

        if format == "csv":
            # Create CSV
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(columns)
            writer.writerows(rows)

            return {
                "format": "csv",
                "data": output.getvalue(),
                "rows": len(rows)
            }
        else:
            # Create JSON
            data = [dict(zip(columns, row)) for row in rows]
            return {
                "format": "json",
                "data": data,
                "rows": len(rows)
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
