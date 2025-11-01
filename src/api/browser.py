"""
Browser extension API endpoints.

Handles communication with browser extensions for domain tracking.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import logging

from src.daemon import get_daemon


logger = logging.getLogger(__name__)
router = APIRouter()


class ActiveTabReport(BaseModel):
    """Active tab report from browser extension."""
    domain: str
    timestamp: int  # Unix timestamp
    browser: str


@router.post("/browser/active-tab")
async def report_active_tab(report: ActiveTabReport):
    """
    Receive active tab report from browser extension.

    Args:
        report: ActiveTabReport containing domain, timestamp, and browser

    Returns:
        Success confirmation
    """
    try:
        # Get daemon instance
        daemon = get_daemon()
        if not daemon:
            raise HTTPException(status_code=503, detail="Daemon not running")

        # Record browser domain usage
        await daemon.record_browser_domain(
            domain=report.domain,
            browser=report.browser
        )

        logger.debug(f"Recorded active tab: {report.domain} ({report.browser})")

        return {
            "status": "success",
            "domain": report.domain,
            "browser": report.browser,
            "timestamp": report.timestamp
        }

    except Exception as e:
        logger.error(f"Error recording active tab: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/browser/status")
async def browser_status():
    """
    Get browser extension status.

    Returns:
        Status information for browser extension connectivity
    """
    daemon = get_daemon()

    return {
        "daemon_running": daemon is not None and daemon.running if daemon else False,
        "api_version": "0.1.0",
        "accepting_reports": True
    }
