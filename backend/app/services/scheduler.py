"""Background scheduler for periodic re-analysis of all configurations.

Disabled by default (SCHEDULED_REANALYSIS_INTERVAL_HOURS=0).
Set SCHEDULED_REANALYSIS_INTERVAL_HOURS to a positive integer to enable.

Design: plain asyncio.Task loop — no extra dependencies.
Each tick fetches all configurations and kicks off a full analysis pipeline
for each one, reusing the same background session pattern as BackgroundTasks.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)

_scheduler_task: asyncio.Task | None = None  # type: ignore[type-arg]


def start_scheduler(settings: Settings) -> None:
    interval_h = settings.scheduled_reanalysis_interval_hours
    if interval_h <= 0:
        logger.debug("Scheduled re-analysis disabled (interval=0)")
        return
    global _scheduler_task
    _scheduler_task = asyncio.create_task(
        _scheduler_loop(interval_h, settings),
        name="scheduled-reanalysis",
    )
    logger.info("Scheduled re-analysis enabled: every %d hour(s)", interval_h)


def stop_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        _scheduler_task = None


async def _scheduler_loop(interval_hours: int, settings: Settings) -> None:
    interval_seconds = interval_hours * 3600
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await _reanalyze_all(settings)
        except Exception as exc:
            logger.error("Scheduled re-analysis error: %s", exc, exc_info=True)


async def _reanalyze_all(settings: Settings) -> None:
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.configuration import Configuration
    from app.services.analysis_pipeline import run_analysis_pipeline

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Configuration))
        configurations = list(result.scalars().all())

    logger.info("Scheduled re-analysis: found %d configurations", len(configurations))

    for config in configurations:
        try:
            async with AsyncSessionLocal() as session:
                await run_analysis_pipeline(config, session, settings)
            logger.info("Scheduled re-analysis: completed config %s (%s)", config.id, config.name)
        except Exception as exc:
            logger.warning(
                "Scheduled re-analysis: failed for config %s: %s", config.id, exc
            )
