"""
Data retention and migration scheduler.

Handles periodic aggregation and cleanup of old data according to
retention policies defined in config.
"""
import asyncio
from datetime import datetime, timedelta
import logging
from typing import Optional

from src.db_queries import (
    create_hourly_aggregates,
    create_daily_aggregates,
    cleanup_old_samples,
    cleanup_old_hourly_aggregates,
    get_config,
    set_config
)
from src.utils import (
    get_hours_to_aggregate,
    get_days_to_aggregate,
    round_to_hour
)


logger = logging.getLogger(__name__)


class RetentionScheduler:
    """
    Manages data retention and aggregation schedules.

    Responsibilities:
    1. Aggregate raw samples into hourly data
    2. Aggregate hourly data into daily data
    3. Clean up old raw samples
    4. Clean up old hourly aggregates
    """

    def __init__(
        self,
        aggregation_interval_seconds: int = 300,  # 5 minutes
        cleanup_interval_seconds: int = 3600,     # 1 hour
    ):
        """
        Initialize retention scheduler.

        Args:
            aggregation_interval_seconds: How often to run aggregation (default 5 min)
            cleanup_interval_seconds: How often to run cleanup (default 1 hour)
        """
        self.aggregation_interval = aggregation_interval_seconds
        self.cleanup_interval = cleanup_interval_seconds
        self.running = False
        self._aggregation_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the retention scheduler tasks."""
        if self.running:
            logger.warning("Retention scheduler already running")
            return

        logger.info("Starting retention scheduler")
        self.running = True

        # Start background tasks
        self._aggregation_task = asyncio.create_task(self._aggregation_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("Retention scheduler started")

    async def stop(self) -> None:
        """Stop the retention scheduler tasks."""
        if not self.running:
            return

        logger.info("Stopping retention scheduler")
        self.running = False

        # Cancel tasks
        if self._aggregation_task:
            self._aggregation_task.cancel()
            try:
                await self._aggregation_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Retention scheduler stopped")

    async def _aggregation_loop(self) -> None:
        """Background task for periodic aggregation."""
        while self.running:
            try:
                await self.run_aggregation()
                await asyncio.sleep(self.aggregation_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in aggregation loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait a bit before retrying

    async def _cleanup_loop(self) -> None:
        """Background task for periodic cleanup."""
        while self.running:
            try:
                await self.run_cleanup()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)
                await asyncio.sleep(300)  # Wait a bit before retrying

    async def run_aggregation(self) -> None:
        """
        Run aggregation process.

        1. Check which hours need aggregation
        2. Create hourly aggregates from raw samples
        3. Check which days need aggregation
        4. Create daily aggregates from hourly data
        """
        logger.debug("Running aggregation process")

        try:
            # Get last aggregation time
            last_agg_str = await get_config('last_aggregation')
            last_agg = datetime.fromisoformat(last_agg_str) if last_agg_str else None

            # Aggregate hourly data
            hours_to_process = get_hours_to_aggregate()
            hourly_count = 0

            for hour_start in hours_to_process:
                # Only aggregate if this hour is after last aggregation
                if last_agg is None or hour_start > last_agg:
                    count = await create_hourly_aggregates(hour_start)
                    if count > 0:
                        hourly_count += count
                        logger.debug(f"Created {count} hourly aggregates for {hour_start}")

            if hourly_count > 0:
                logger.info(f"Created {hourly_count} hourly aggregates")

            # Aggregate daily data
            days_to_process = get_days_to_aggregate()
            daily_count = 0

            for day_start in days_to_process:
                count = await create_daily_aggregates(day_start)
                if count > 0:
                    daily_count += count
                    logger.debug(f"Created {count} daily aggregates for {day_start}")

            if daily_count > 0:
                logger.info(f"Created {daily_count} daily aggregates")

            # Update last aggregation timestamp
            await set_config('last_aggregation', datetime.now().isoformat())

        except Exception as e:
            logger.error(f"Error during aggregation: {e}", exc_info=True)

    async def run_cleanup(self) -> None:
        """
        Run cleanup process.

        1. Get retention policies from config
        2. Clean up old raw samples
        3. Clean up old hourly aggregates
        """
        logger.debug("Running cleanup process")

        try:
            # Get retention policies
            raw_retention_str = await get_config('data_retention_days_raw')
            hourly_retention_str = await get_config('data_retention_days_hourly')

            raw_retention = int(raw_retention_str) if raw_retention_str else 7
            hourly_retention = int(hourly_retention_str) if hourly_retention_str else 90

            # Clean up old samples
            deleted_samples = await cleanup_old_samples(raw_retention)
            if deleted_samples > 0:
                logger.info(f"Cleaned up {deleted_samples} old raw samples (>{raw_retention} days)")

            # Clean up old hourly aggregates
            deleted_hourly = await cleanup_old_hourly_aggregates(hourly_retention)
            if deleted_hourly > 0:
                logger.info(f"Cleaned up {deleted_hourly} old hourly aggregates (>{hourly_retention} days)")

            # Update last cleanup timestamp
            await set_config('last_cleanup', datetime.now().isoformat())

        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)

    async def force_aggregation_now(self) -> None:
        """Force immediate aggregation (useful for testing or manual triggers)."""
        logger.info("Forcing immediate aggregation")
        await self.run_aggregation()

    async def force_cleanup_now(self) -> None:
        """Force immediate cleanup (useful for testing or manual triggers)."""
        logger.info("Forcing immediate cleanup")
        await self.run_cleanup()


# Convenience functions for one-off operations

async def aggregate_all_pending() -> dict:
    """
    Aggregate all pending data.

    Returns:
        Dictionary with counts of aggregates created.
    """
    logger.info("Running full aggregation")

    hourly_count = 0
    daily_count = 0

    # Aggregate all hours
    hours = get_hours_to_aggregate()
    for hour_start in hours:
        count = await create_hourly_aggregates(hour_start)
        hourly_count += count

    # Aggregate all days
    days = get_days_to_aggregate()
    for day_start in days:
        count = await create_daily_aggregates(day_start)
        daily_count += count

    result = {
        'hourly_aggregates': hourly_count,
        'daily_aggregates': daily_count
    }

    logger.info(f"Aggregation complete: {result}")
    return result


async def cleanup_all_old_data(raw_days: int = 7, hourly_days: int = 90) -> dict:
    """
    Clean up all old data according to retention policies.

    Args:
        raw_days: Retention period for raw samples (default 7 days)
        hourly_days: Retention period for hourly aggregates (default 90 days)

    Returns:
        Dictionary with counts of records deleted.
    """
    logger.info(f"Cleaning up data older than {raw_days} days (raw) and {hourly_days} days (hourly)")

    deleted_samples = await cleanup_old_samples(raw_days)
    deleted_hourly = await cleanup_old_hourly_aggregates(hourly_days)

    result = {
        'deleted_samples': deleted_samples,
        'deleted_hourly': deleted_hourly
    }

    logger.info(f"Cleanup complete: {result}")
    return result
