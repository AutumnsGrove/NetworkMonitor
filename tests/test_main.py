"""Tests for main entry point."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import threading


def test_main_imports():
    """Test that main.py imports successfully."""
    import main
    assert main is not None


def test_logging_config():
    """Test logging configuration."""
    from src.logging_config import setup_logging

    logger = setup_logging(debug=True, log_to_console=False)
    assert logger is not None
    assert logger.level == 10  # DEBUG level


def test_network_monitor_app_class():
    """Test NetworkMonitorApp class exists and can be instantiated."""
    from main import NetworkMonitorApp

    # Mock the setup_logging to avoid file I/O during tests
    with patch('main.setup_logging') as mock_logging:
        mock_logging.return_value = MagicMock()
        app = NetworkMonitorApp(debug=True, no_menubar=True, port=8000)

        assert app.debug is True
        assert app.no_menubar is True
        assert app.port == 8000
        assert app.daemon is None
        assert app.webserver_thread is None
        assert app.menubar is None
        assert app.scheduler is None


def test_cli_argument_parsing():
    """Test CLI argument parsing."""
    from main import main
    # Can't easily test argparse without mocking sys.argv
    # This just verifies import works
    assert callable(main)


def test_shutdown_event():
    """Test that shutdown_event is a threading.Event."""
    from main import shutdown_event

    assert isinstance(shutdown_event, threading.Event)
    assert not shutdown_event.is_set()


def test_signal_handler():
    """Test signal handler sets shutdown_event."""
    from main import NetworkMonitorApp, shutdown_event

    with patch('main.setup_logging') as mock_logging:
        mock_logging.return_value = MagicMock()
        app = NetworkMonitorApp(debug=False, no_menubar=True)

        # Clear shutdown_event
        shutdown_event.clear()

        # Call signal handler
        app._handle_signal(15, None)  # SIGTERM

        # Verify shutdown_event was set
        assert shutdown_event.is_set()

        # Clean up
        shutdown_event.clear()


def test_initialize_creates_directory():
    """Test that initialize creates .netmonitor directory."""
    from main import NetworkMonitorApp
    from pathlib import Path

    with patch('main.setup_logging') as mock_logging, \
         patch('main.init_database') as mock_init_db, \
         patch('main.asyncio.run') as mock_asyncio_run:

        mock_logging.return_value = MagicMock()
        mock_asyncio_run.return_value = None

        app = NetworkMonitorApp(debug=False, no_menubar=True)
        app.initialize()

        # Verify .netmonitor directory exists
        netmonitor_dir = Path.home() / ".netmonitor"
        assert netmonitor_dir.exists()


def test_app_component_references():
    """Test that app maintains references to components."""
    from main import NetworkMonitorApp

    with patch('main.setup_logging') as mock_logging:
        mock_logging.return_value = MagicMock()
        app = NetworkMonitorApp()

        # All components should start as None
        assert app.daemon is None
        assert app.webserver_thread is None
        assert app.menubar is None
        assert app.scheduler is None


def test_debug_mode_enables_debug_logging():
    """Test that debug mode passes through to logging."""
    from main import NetworkMonitorApp

    with patch('main.setup_logging') as mock_logging:
        mock_logging.return_value = MagicMock()

        app = NetworkMonitorApp(debug=True)

        # Verify setup_logging was called with debug=True
        mock_logging.assert_called_once_with(debug=True, log_to_console=True)


def test_port_configuration():
    """Test that custom port is stored."""
    from main import NetworkMonitorApp

    with patch('main.setup_logging') as mock_logging:
        mock_logging.return_value = MagicMock()

        app = NetworkMonitorApp(port=9000)

        assert app.port == 9000


def test_default_port():
    """Test default port is 7500."""
    from main import NetworkMonitorApp

    with patch('main.setup_logging') as mock_logging:
        mock_logging.return_value = MagicMock()

        app = NetworkMonitorApp()

        assert app.port == 7500
