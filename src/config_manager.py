"""
Configuration Manager for Network Monitor

Provides centralized configuration management with:
- YAML file loading from ~/.netmonitor/config.yaml
- Database configuration overrides
- Sensible fallback defaults
- Singleton pattern for global access
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DaemonConfig:
    """Daemon configuration settings."""
    sampling_interval_seconds: int = 1
    enable_retention: bool = True


@dataclass
class ServerConfig:
    """Web server configuration settings."""
    port: int = 7500
    host: str = "localhost"


@dataclass
class RetentionConfig:
    """Data retention policy settings."""
    raw_samples_days: int = 7
    hourly_aggregates_days: int = 90
    aggregation_interval_seconds: int = 300
    cleanup_interval_seconds: int = 3600


@dataclass
class MenuBarConfig:
    """MenuBar application settings."""
    refresh_interval_seconds: int = 30
    high_usage_threshold_mb: float = 50.0
    notification_cooldown_seconds: int = 300


@dataclass
class DashboardConfig:
    """Dashboard refresh settings."""
    overview_refresh_ms: int = 30000
    config_refresh_ms: int = 10000


@dataclass
class APIConfig:
    """API settings."""
    default_timeout_seconds: int = 3


@dataclass
class ProcessMapperConfig:
    """Process mapper timeout settings."""
    lsof_timeout_seconds: int = 5
    ps_timeout_seconds: int = 2
    bundle_timeout_seconds: int = 1


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    max_file_size_mb: int = 10
    backup_count: int = 5


@dataclass
class ExtensionConfig:
    """Browser extension settings."""
    enabled: bool = True


@dataclass
class NotificationsConfig:
    """Notification settings."""
    enabled: bool = False
    high_usage_enabled: bool = True


@dataclass
class Config:
    """Main configuration container."""
    daemon: DaemonConfig = field(default_factory=DaemonConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    retention: RetentionConfig = field(default_factory=RetentionConfig)
    menubar: MenuBarConfig = field(default_factory=MenuBarConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    api: APIConfig = field(default_factory=APIConfig)
    process_mapper: ProcessMapperConfig = field(default_factory=ProcessMapperConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    extension: ExtensionConfig = field(default_factory=ExtensionConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)

    _config_source: Dict[str, str] = field(default_factory=dict)

    def get_config_source(self, key: str) -> str:
        """Get the source of a configuration value (file/database/default)."""
        return self._config_source.get(key, "default")

    def set_config_source(self, key: str, source: str):
        """Set the source of a configuration value."""
        self._config_source[key] = source


class ConfigManager:
    """
    Singleton configuration manager.

    Loads configuration from:
    1. Default values (defined in dataclasses)
    2. YAML file (~/.netmonitor/config.yaml)
    3. Database overrides (loaded via merge_database_config)

    Priority: Database > File > Defaults
    """

    _instance: Optional['ConfigManager'] = None
    _config: Optional[Config] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self._config = self._load_config()

    @property
    def config(self) -> Config:
        """Get the current configuration."""
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def reload(self):
        """Reload configuration from file."""
        self._config = self._load_config()
        logger.info("Configuration reloaded")

    def _get_config_path(self) -> Path:
        """Get the path to the configuration file in the project directory."""
        # Get project root (one level up from src/)
        project_root = Path(__file__).parent.parent
        return project_root / "config.yaml"

    def _load_config(self) -> Config:
        """Load configuration from YAML file with fallback to defaults."""
        config = Config()
        config_path = self._get_config_path()

        if not config_path.exists():
            logger.warning(f"Config file not found at {config_path}, using defaults")
            return config

        try:
            with open(config_path, 'r') as f:
                yaml_data = yaml.safe_load(f)

            if not yaml_data:
                logger.warning("Config file is empty, using defaults")
                return config

            # Load each section
            if 'daemon' in yaml_data:
                config.daemon = DaemonConfig(**yaml_data['daemon'])
                for key in yaml_data['daemon']:
                    config.set_config_source(f"daemon.{key}", "file")

            if 'server' in yaml_data:
                config.server = ServerConfig(**yaml_data['server'])
                for key in yaml_data['server']:
                    config.set_config_source(f"server.{key}", "file")

            if 'retention' in yaml_data:
                config.retention = RetentionConfig(**yaml_data['retention'])
                for key in yaml_data['retention']:
                    config.set_config_source(f"retention.{key}", "file")

            if 'menubar' in yaml_data:
                config.menubar = MenuBarConfig(**yaml_data['menubar'])
                for key in yaml_data['menubar']:
                    config.set_config_source(f"menubar.{key}", "file")

            if 'dashboard' in yaml_data:
                config.dashboard = DashboardConfig(**yaml_data['dashboard'])
                for key in yaml_data['dashboard']:
                    config.set_config_source(f"dashboard.{key}", "file")

            if 'api' in yaml_data:
                config.api = APIConfig(**yaml_data['api'])
                for key in yaml_data['api']:
                    config.set_config_source(f"api.{key}", "file")

            if 'process_mapper' in yaml_data:
                config.process_mapper = ProcessMapperConfig(**yaml_data['process_mapper'])
                for key in yaml_data['process_mapper']:
                    config.set_config_source(f"process_mapper.{key}", "file")

            if 'logging' in yaml_data:
                config.logging = LoggingConfig(**yaml_data['logging'])
                for key in yaml_data['logging']:
                    config.set_config_source(f"logging.{key}", "file")

            if 'extension' in yaml_data:
                config.extension = ExtensionConfig(**yaml_data['extension'])
                for key in yaml_data['extension']:
                    config.set_config_source(f"extension.{key}", "file")

            if 'notifications' in yaml_data:
                config.notifications = NotificationsConfig(**yaml_data['notifications'])
                for key in yaml_data['notifications']:
                    config.set_config_source(f"notifications.{key}", "file")

            logger.info(f"Configuration loaded from {config_path}")

        except yaml.YAMLError as e:
            logger.error(f"Error parsing config file: {e}, using defaults")
        except Exception as e:
            logger.error(f"Error loading config file: {e}, using defaults")

        return config

    def merge_database_config(self, db_config: Dict[str, Any]):
        """
        Merge database configuration values.
        Database values override file/default values.

        Args:
            db_config: Dictionary of config values from database
        """
        if not db_config:
            return

        config = self.config

        # Map database keys to config attributes
        # Format: "section.key" -> config.section.key
        for key, value in db_config.items():
            try:
                if '.' in key:
                    section, attr = key.split('.', 1)
                    if hasattr(config, section):
                        section_obj = getattr(config, section)
                        if hasattr(section_obj, attr):
                            setattr(section_obj, attr, value)
                            config.set_config_source(key, "database")
                            logger.debug(f"Applied database override for {key}: {value}")
            except Exception as e:
                logger.error(f"Error applying database config for {key}: {e}")

    def get_all_config_values(self) -> Dict[str, Any]:
        """
        Get all configuration values as a flat dictionary.

        Returns:
            Dictionary with keys in "section.key" format
        """
        config = self.config
        result = {}

        # Daemon
        for attr in ['sampling_interval_seconds', 'enable_retention']:
            result[f"daemon.{attr}"] = getattr(config.daemon, attr)

        # Server
        for attr in ['port', 'host']:
            result[f"server.{attr}"] = getattr(config.server, attr)

        # Retention
        for attr in ['raw_samples_days', 'hourly_aggregates_days',
                     'aggregation_interval_seconds', 'cleanup_interval_seconds']:
            result[f"retention.{attr}"] = getattr(config.retention, attr)

        # MenuBar
        for attr in ['refresh_interval_seconds', 'high_usage_threshold_mb',
                     'notification_cooldown_seconds']:
            result[f"menubar.{attr}"] = getattr(config.menubar, attr)

        # Dashboard
        for attr in ['overview_refresh_ms', 'config_refresh_ms']:
            result[f"dashboard.{attr}"] = getattr(config.dashboard, attr)

        # API
        for attr in ['default_timeout_seconds']:
            result[f"api.{attr}"] = getattr(config.api, attr)

        # Process Mapper
        for attr in ['lsof_timeout_seconds', 'ps_timeout_seconds', 'bundle_timeout_seconds']:
            result[f"process_mapper.{attr}"] = getattr(config.process_mapper, attr)

        # Logging
        for attr in ['level', 'max_file_size_mb', 'backup_count']:
            result[f"logging.{attr}"] = getattr(config.logging, attr)

        # Extension
        for attr in ['enabled']:
            result[f"extension.{attr}"] = getattr(config.extension, attr)

        # Notifications
        for attr in ['enabled', 'high_usage_enabled']:
            result[f"notifications.{attr}"] = getattr(config.notifications, attr)

        return result


# Singleton instance getter
def get_config() -> Config:
    """Get the global configuration instance."""
    return ConfigManager().config


def get_config_manager() -> ConfigManager:
    """Get the global ConfigManager instance."""
    return ConfigManager()
