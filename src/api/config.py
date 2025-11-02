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
