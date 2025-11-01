# NetworkMonitor

A lightweight, privacy-focused network monitoring tool for macOS that tracks application-level network usage with enhanced domain-level tracking for web browsers.

## Features

- **Application-Level Tracking**: Monitor network usage per application with 5-second sampling
- **Domain-Level Browser Tracking**: Identify high-traffic domains for web browsers (Zen browser support via extension)
- **Rich Web Dashboard**: FastAPI + Plotly/Dash visualization interface at localhost:7500
- **Privacy-First Design**: All data stays local, no external API calls, no telemetry
- **MenuBar Integration**: macOS menubar app for quick status and dashboard access
- **Automatic Data Retention**: Smart aggregation (raw → hourly → daily) with configurable retention policies
- **Auto-Start Support**: macOS LaunchAgent for background operation

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, SQLite, aiosqlite
- **Visualization**: Plotly, Dash
- **Network Capture**: scapy (packet sniffing)
- **MenuBar**: rumps
- **Package Management**: uv

## Quick Start

```bash
# Initialize dependencies
uv sync

# Run (requires sudo for packet capture)
sudo uv run python main.py

# Access dashboard
# Opens automatically at http://127.0.0.1:7500
```

## Project Structure

See `network-monitor-spec.md` for complete specification and `network-monitor-agentic-guide.md` for development strategy.

## Documentation

- `CLAUDE.md` - Project context and instructions
- `TODOS.md` - Task list
- `network-monitor-spec.md` - Full project specification
- `network-monitor-agentic-guide.md` - Development guide
- `ClaudeUsage/` - Comprehensive workflow guides

## Development Roadmap

1. **Phase 1**: Core Daemon (packet capture, database, aggregation)
2. **Phase 2**: Web Dashboard (FastAPI, visualizations)
3. **Phase 3**: MenuBar App (macOS integration)
4. **Phase 4**: Browser Extension (Zen browser)
5. **Phase 5**: Auto-Start & Polish (LaunchAgent, logging, error handling)

## Next Steps

See `TODOS.md` for your checklist!
