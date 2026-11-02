"""Startup check: find configurations whose latest analysis used an old rule version
and trigger re-analysis for each one.

Called once from the FastAPI lifespan at startup. Never raises — errors are logged.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)


async def reanalyze_stale_configurations(settings: Settings) -> None:
    """Fetch every configuration, check its latest analysis rule_version against the
    current RULE_VERSIONS dict, and queue a new analysis for any that are stale."""
    from sqlalchemy import select

    from app.analyzers.factory import RULE_VERSIONS
    from app.db.session import AsyncSessionLocal
    from app.models.analysis import Analysis
    from app.models.configuration import Configuration
    from app.schemas.finding import ConfigurationType
    from app.services.analysis_pipeline import run_analysis_pipeline

    stale: list[Configuration] = []

    async with AsyncSessionLocal() as session:
        configs_result = await session.execute(select(Configuration))
        configurations = list(configs_result.scalars().all())

        for config in configurations:
            try:
                config_type = ConfigurationType(config.configuration_type)
            except ValueError:
                continue
            current_version = RULE_VERSIONS.get(config_type)
            if current_version is None:
                continue

            latest_result = await session.execute(
                select(Analysis)
                .where(Analysis.configuration_id == config.id)
                .order_by(Analysis.created_at.desc())
                .limit(1)
            )
            latest = latest_result.scalar_one_or_none()

            if latest is None or latest.rule_version != current_version:
                stale.append(config)

    if not stale:
        logger.info("Rule-update check: all configurations are up to date")
        return

    logger.info(
        "Rule-update check: %d configuration(s) have stale analyses — queuing re-analysis",
        len(stale),
    )

    for config in stale:
        await asyncio.sleep(0)  # yield to the event loop between jobs
        try:
            async with AsyncSessionLocal() as session:
                await run_analysis_pipeline(config, session, settings)
            logger.info(
                "Rule-update re-analysis completed for config %s (%s)", config.id, config.name
            )
        except Exception as exc:
            logger.warning(
                "Rule-update re-analysis failed for config %s: %s", config.id, exc
            )
