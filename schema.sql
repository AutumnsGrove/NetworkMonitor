-- Network Monitor Database Schema
-- SQLite database for storing network usage data
-- Location: ~/.netmonitor/network_monitor.db

-- Schema version tracking for migrations
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Insert initial schema version
INSERT OR IGNORE INTO schema_version (version, description)
VALUES (1, 'Initial schema with network samples, aggregates, applications, and domains');

-- Application metadata
CREATE TABLE IF NOT EXISTS applications (
    app_id INTEGER PRIMARY KEY AUTOINCREMENT,
    process_name TEXT NOT NULL,
    bundle_id TEXT,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(process_name, bundle_id)
);

CREATE INDEX IF NOT EXISTS idx_applications_process_name ON applications(process_name);
CREATE INDEX IF NOT EXISTS idx_applications_last_seen ON applications(last_seen);

-- Domain tracking for browsers
CREATE TABLE IF NOT EXISTS domains (
    domain_id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL UNIQUE,
    parent_domain TEXT,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_domains_domain ON domains(domain);
CREATE INDEX IF NOT EXISTS idx_domains_parent ON domains(parent_domain);

-- Raw network samples (5-second intervals)
-- Retention: 7 days, then migrate to hourly aggregates
CREATE TABLE IF NOT EXISTS network_samples (
    sample_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    app_id INTEGER NOT NULL,
    bytes_sent INTEGER DEFAULT 0,
    bytes_received INTEGER DEFAULT 0,
    packets_sent INTEGER DEFAULT 0,
    packets_received INTEGER DEFAULT 0,
    active_connections INTEGER DEFAULT 0,
    FOREIGN KEY (app_id) REFERENCES applications(app_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_samples_timestamp ON network_samples(timestamp);
CREATE INDEX IF NOT EXISTS idx_samples_app_id ON network_samples(app_id);
CREATE INDEX IF NOT EXISTS idx_samples_app_timestamp ON network_samples(app_id, timestamp);

-- Browser domain samples (correlates browser activity with domains)
CREATE TABLE IF NOT EXISTS browser_domain_samples (
    sample_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    domain_id INTEGER NOT NULL,
    app_id INTEGER NOT NULL,
    bytes_sent INTEGER DEFAULT 0,
    bytes_received INTEGER DEFAULT 0,
    FOREIGN KEY (domain_id) REFERENCES domains(domain_id) ON DELETE CASCADE,
    FOREIGN KEY (app_id) REFERENCES applications(app_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_browser_samples_timestamp ON browser_domain_samples(timestamp);
CREATE INDEX IF NOT EXISTS idx_browser_samples_domain ON browser_domain_samples(domain_id);
CREATE INDEX IF NOT EXISTS idx_browser_samples_app ON browser_domain_samples(app_id);

-- Hourly aggregates
-- Retention: 30-90 days (configurable)
CREATE TABLE IF NOT EXISTS hourly_aggregates (
    aggregate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    hour_start TIMESTAMP NOT NULL,
    app_id INTEGER NOT NULL,
    bytes_sent INTEGER DEFAULT 0,
    bytes_received INTEGER DEFAULT 0,
    packets_sent INTEGER DEFAULT 0,
    packets_received INTEGER DEFAULT 0,
    max_active_connections INTEGER DEFAULT 0,
    sample_count INTEGER DEFAULT 0,
    FOREIGN KEY (app_id) REFERENCES applications(app_id) ON DELETE CASCADE,
    UNIQUE(hour_start, app_id)
);

CREATE INDEX IF NOT EXISTS idx_hourly_hour_start ON hourly_aggregates(hour_start);
CREATE INDEX IF NOT EXISTS idx_hourly_app_id ON hourly_aggregates(app_id);

-- Browser domain hourly aggregates
CREATE TABLE IF NOT EXISTS browser_domain_hourly (
    aggregate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    hour_start TIMESTAMP NOT NULL,
    domain_id INTEGER NOT NULL,
    app_id INTEGER NOT NULL,
    bytes_sent INTEGER DEFAULT 0,
    bytes_received INTEGER DEFAULT 0,
    sample_count INTEGER DEFAULT 0,
    FOREIGN KEY (domain_id) REFERENCES domains(domain_id) ON DELETE CASCADE,
    FOREIGN KEY (app_id) REFERENCES applications(app_id) ON DELETE CASCADE,
    UNIQUE(hour_start, domain_id, app_id)
);

CREATE INDEX IF NOT EXISTS idx_browser_hourly_hour ON browser_domain_hourly(hour_start);
CREATE INDEX IF NOT EXISTS idx_browser_hourly_domain ON browser_domain_hourly(domain_id);

-- Daily aggregates
-- Retention: Indefinite (minimal storage)
CREATE TABLE IF NOT EXISTS daily_aggregates (
    aggregate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    day_start DATE NOT NULL,
    app_id INTEGER NOT NULL,
    bytes_sent INTEGER DEFAULT 0,
    bytes_received INTEGER DEFAULT 0,
    packets_sent INTEGER DEFAULT 0,
    packets_received INTEGER DEFAULT 0,
    max_active_connections INTEGER DEFAULT 0,
    sample_count INTEGER DEFAULT 0,
    FOREIGN KEY (app_id) REFERENCES applications(app_id) ON DELETE CASCADE,
    UNIQUE(day_start, app_id)
);

CREATE INDEX IF NOT EXISTS idx_daily_day_start ON daily_aggregates(day_start);
CREATE INDEX IF NOT EXISTS idx_daily_app_id ON daily_aggregates(app_id);

-- Browser domain daily aggregates
CREATE TABLE IF NOT EXISTS browser_domain_daily (
    aggregate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    day_start DATE NOT NULL,
    domain_id INTEGER NOT NULL,
    app_id INTEGER NOT NULL,
    bytes_sent INTEGER DEFAULT 0,
    bytes_received INTEGER DEFAULT 0,
    sample_count INTEGER DEFAULT 0,
    FOREIGN KEY (domain_id) REFERENCES domains(domain_id) ON DELETE CASCADE,
    FOREIGN KEY (app_id) REFERENCES applications(app_id) ON DELETE CASCADE,
    UNIQUE(day_start, domain_id, app_id)
);

CREATE INDEX IF NOT EXISTS idx_browser_daily_day ON browser_domain_daily(day_start);
CREATE INDEX IF NOT EXISTS idx_browser_daily_domain ON browser_domain_daily(domain_id);

-- Configuration storage
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default configuration
INSERT OR IGNORE INTO config (key, value) VALUES
    ('sampling_interval_seconds', '5'),
    ('data_retention_days_raw', '7'),
    ('data_retention_days_hourly', '90'),
    ('last_cleanup', datetime('now')),
    ('last_aggregation', datetime('now'));

-- Active browser tab tracking (for correlating domains with usage)
CREATE TABLE IF NOT EXISTS active_tabs (
    tab_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    domain_id INTEGER NOT NULL,
    browser TEXT NOT NULL,
    FOREIGN KEY (domain_id) REFERENCES domains(domain_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_active_tabs_timestamp ON active_tabs(timestamp);
CREATE INDEX IF NOT EXISTS idx_active_tabs_domain ON active_tabs(domain_id);

-- Data retention tracking
CREATE TABLE IF NOT EXISTS retention_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    records_affected INTEGER DEFAULT 0,
    details TEXT
);
