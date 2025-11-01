"""
Pydantic data models for Network Monitor.

These models define the structure of data flowing through the system,
ensuring type safety and validation.
"""
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class Application(BaseModel):
    """Application metadata model."""
    app_id: Optional[int] = None
    process_name: str
    bundle_id: Optional[str] = None
    first_seen: datetime = Field(default_factory=datetime.now)
    last_seen: datetime = Field(default_factory=datetime.now)

    @field_validator('process_name')
    @classmethod
    def validate_process_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Process name cannot be empty")
        return v.strip()


class Domain(BaseModel):
    """Domain tracking model."""
    domain_id: Optional[int] = None
    domain: str
    parent_domain: Optional[str] = None
    first_seen: datetime = Field(default_factory=datetime.now)
    last_seen: datetime = Field(default_factory=datetime.now)

    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Domain cannot be empty")
        # Basic domain validation
        domain = v.strip().lower()
        if '/' in domain or ' ' in domain:
            raise ValueError("Domain should not contain paths or spaces")
        return domain


class NetworkSample(BaseModel):
    """Raw network sample (5-second interval)."""
    sample_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    app_id: int
    bytes_sent: int = 0
    bytes_received: int = 0
    packets_sent: int = 0
    packets_received: int = 0
    active_connections: int = 0

    @field_validator('bytes_sent', 'bytes_received', 'packets_sent',
                     'packets_received', 'active_connections')
    @classmethod
    def validate_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Value cannot be negative")
        return v


class BrowserDomainSample(BaseModel):
    """Browser domain sample (correlates browser activity with domains)."""
    sample_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    domain_id: int
    app_id: int
    bytes_sent: int = 0
    bytes_received: int = 0

    @field_validator('bytes_sent', 'bytes_received')
    @classmethod
    def validate_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Value cannot be negative")
        return v


class HourlyAggregate(BaseModel):
    """Hourly aggregated network usage."""
    aggregate_id: Optional[int] = None
    hour_start: datetime
    app_id: int
    bytes_sent: int = 0
    bytes_received: int = 0
    packets_sent: int = 0
    packets_received: int = 0
    max_active_connections: int = 0
    sample_count: int = 0

    @field_validator('bytes_sent', 'bytes_received', 'packets_sent',
                     'packets_received', 'max_active_connections', 'sample_count')
    @classmethod
    def validate_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Value cannot be negative")
        return v


class BrowserDomainHourly(BaseModel):
    """Hourly browser domain aggregates."""
    aggregate_id: Optional[int] = None
    hour_start: datetime
    domain_id: int
    app_id: int
    bytes_sent: int = 0
    bytes_received: int = 0
    sample_count: int = 0


class DailyAggregate(BaseModel):
    """Daily aggregated network usage."""
    aggregate_id: Optional[int] = None
    day_start: date
    app_id: int
    bytes_sent: int = 0
    bytes_received: int = 0
    packets_sent: int = 0
    packets_received: int = 0
    max_active_connections: int = 0
    sample_count: int = 0


class BrowserDomainDaily(BaseModel):
    """Daily browser domain aggregates."""
    aggregate_id: Optional[int] = None
    day_start: date
    domain_id: int
    app_id: int
    bytes_sent: int = 0
    bytes_received: int = 0
    sample_count: int = 0


class ActiveTab(BaseModel):
    """Active browser tab tracking."""
    tab_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    domain_id: int
    browser: str

    @field_validator('browser')
    @classmethod
    def validate_browser(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Browser name cannot be empty")
        return v.strip().lower()


class Config(BaseModel):
    """Configuration key-value pair."""
    key: str
    value: str
    updated_at: datetime = Field(default_factory=datetime.now)


class RetentionLog(BaseModel):
    """Data retention operation log."""
    log_id: Optional[int] = None
    operation: str
    timestamp: datetime = Field(default_factory=datetime.now)
    records_affected: int = 0
    details: Optional[str] = None


# Statistics and aggregation models for API responses
class AppUsageStats(BaseModel):
    """Application usage statistics."""
    app_id: int
    process_name: str
    total_bytes_sent: int = 0
    total_bytes_received: int = 0
    total_bytes: int = 0
    total_packets_sent: int = 0
    total_packets_received: int = 0
    first_seen: datetime
    last_seen: datetime


class DomainUsageStats(BaseModel):
    """Domain usage statistics."""
    domain_id: int
    domain: str
    parent_domain: Optional[str] = None
    total_bytes_sent: int = 0
    total_bytes_received: int = 0
    total_bytes: int = 0
    first_seen: datetime
    last_seen: datetime


class TimeSeriesPoint(BaseModel):
    """Time series data point for visualizations."""
    timestamp: datetime
    bytes_sent: int = 0
    bytes_received: int = 0
    total_bytes: int = 0


class QuickStats(BaseModel):
    """Quick statistics for menubar and dashboard."""
    total_bytes_today: int = 0
    total_bytes_this_week: int = 0
    total_bytes_this_month: int = 0
    top_app_today: Optional[str] = None
    top_domain_today: Optional[str] = None
    active_connections: int = 0
    monitoring_since: Optional[datetime] = None
