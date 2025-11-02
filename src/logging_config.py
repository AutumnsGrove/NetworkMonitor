"""Centralized logging configuration for Network Monitor."""

import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging(debug: bool = False, log_to_console: bool = True):
    """
    Configure logging for all components.

    Args:
        debug: Enable DEBUG level logging
        log_to_console: Also log to console (in addition to file)

    Returns:
        Root logger instance
    """
    # Create logs directory
    log_dir = Path.home() / ".netmonitor" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Clear existing handlers
    root_logger.handlers.clear()

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "network_monitor.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Console handler (if enabled)
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    return root_logger
