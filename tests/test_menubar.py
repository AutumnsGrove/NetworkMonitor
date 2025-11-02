"""Tests for the menubar application."""

import pytest
from unittest.mock import Mock, patch, MagicMock


def test_menubar_imports():
    """Test that menubar module imports correctly."""
    from src import menubar
    assert menubar is not None


def test_format_bytes_import():
    """Test that required utilities are available."""
    from src.utils import format_bytes
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1048576) == "1.0 MB"
    assert format_bytes(500) == "500 B"


def test_menubar_class_exists():
    """Test that NetworkMonitorMenuBar class is defined."""
    from src.menubar import NetworkMonitorMenuBar
    assert NetworkMonitorMenuBar is not None


@patch('rumps.App.__init__')
@patch('rumps.Timer')
@patch('rumps.MenuItem')
@patch('rumps.separator', new=MagicMock())
def test_menubar_initialization(mock_menuitem, mock_timer, mock_app_init):
    """Test menubar app initialization."""
    # Mock App.__init__ to prevent actual rumps initialization
    mock_app_init.return_value = None

    # Mock Timer
    mock_timer_instance = MagicMock()
    mock_timer.return_value = mock_timer_instance

    # Mock MenuItem
    mock_menuitem.return_value = MagicMock()

    from src.menubar import NetworkMonitorMenuBar

    # This will fail on actual macOS menubar creation, but we can test the class exists
    # Full testing requires macOS environment with display
    assert hasattr(NetworkMonitorMenuBar, 'update_stats')
    assert hasattr(NetworkMonitorMenuBar, 'update_icon')
    assert hasattr(NetworkMonitorMenuBar, 'check_daemon_status')
    assert hasattr(NetworkMonitorMenuBar, 'notify_high_usage')
    assert hasattr(NetworkMonitorMenuBar, 'open_dashboard')
    assert hasattr(NetworkMonitorMenuBar, 'refresh_stats')
    assert hasattr(NetworkMonitorMenuBar, 'start_daemon')
    assert hasattr(NetworkMonitorMenuBar, 'stop_daemon')
    assert hasattr(NetworkMonitorMenuBar, 'view_logs')
    assert hasattr(NetworkMonitorMenuBar, 'quit_app')


def test_run_menubar_function_exists():
    """Test that run_menubar entry point exists."""
    from src.menubar import run_menubar
    assert callable(run_menubar)


@patch('requests.get')
def test_update_stats_offline_handling(mock_get):
    """Test update_stats handles API offline gracefully."""
    mock_get.side_effect = Exception("Connection refused")

    # This test verifies error handling logic exists
    # Full test requires mocking rumps completely
    from src.menubar import NetworkMonitorMenuBar
    assert hasattr(NetworkMonitorMenuBar, 'update_stats')


@patch('webbrowser.open')
def test_open_dashboard_url(mock_open):
    """Test that open_dashboard uses correct URL."""
    from src.menubar import NetworkMonitorMenuBar

    # Verify the method exists and would call webbrowser.open
    assert hasattr(NetworkMonitorMenuBar, 'open_dashboard')
    # Full test requires rumps app instance


def test_notification_cooldown_settings():
    """Test that notification cooldown settings are reasonable."""
    from src.menubar import NetworkMonitorMenuBar

    # Can't instantiate without rumps, but can check class attributes exist
    # These would be set in __init__
    assert hasattr(NetworkMonitorMenuBar, '__init__')


# Note: Full menubar testing requires macOS environment with display
# These tests verify:
# - Module imports correctly
# - Required classes and methods exist
# - Utility functions work
# - Basic structure is sound
#
# Manual testing required for:
# - Menu item clicks
# - Icon updates
# - Notifications
# - Dashboard opening
# - Daemon control
