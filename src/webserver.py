"""
FastAPI web server for Network Monitor dashboard and API.

Serves both the REST API for data access and will integrate with
the Dash dashboard for visualization.
"""
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from src.db_queries import init_database
from src.daemon import get_daemon


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown tasks.
    """
    # Startup
    logger.info("Starting web server")

    # Initialize database if needed
    try:
        init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)

    yield

    # Shutdown
    logger.info("Shutting down web server")


# Create FastAPI application
app = FastAPI(
    title="Network Monitor API",
    description="Privacy-focused network monitoring with application-level tracking",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware (allow localhost access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    daemon = get_daemon()
    daemon_status = daemon.get_status() if daemon else {"running": False}

    return {
        "status": "healthy",
        "daemon": daemon_status
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - redirect to docs."""
    return {
        "message": "Network Monitor API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


# Import and include API routers
from src.api import stats, applications, domains, browser, config as config_routes

app.include_router(stats.router, prefix="/api", tags=["stats"])
app.include_router(applications.router, prefix="/api", tags=["applications"])
app.include_router(domains.router, prefix="/api", tags=["domains"])
app.include_router(browser.router, prefix="/api", tags=["browser"])
app.include_router(config_routes.router, prefix="/api", tags=["config"])


def run_server(
    host: str = "127.0.0.1",
    port: int = 7500,
    reload: bool = False,
    log_level: str = "info"
) -> None:
    """
    Run the FastAPI server with uvicorn.

    Args:
        host: Host to bind to (default: 127.0.0.1 for localhost only)
        port: Port to listen on (default: 7500)
        reload: Enable auto-reload (development)
        log_level: Logging level
    """
    logger.info(f"Starting FastAPI server on {host}:{port}")

    uvicorn.run(
        "src.webserver:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        access_log=True
    )


if __name__ == "__main__":
    # Run server directly for testing
    run_server(reload=True)
