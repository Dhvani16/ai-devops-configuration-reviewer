"""Analysis pipeline: static analysis → AI analysis → risk scoring → DB persistence."""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.provider import AIProvider, AIProviderError
from app.ai.schemas import AIAnalysisRequest
from app.analyzers.factory import get_analyzer
from app.analyzers.interface import (
    InvalidConfigurationError,  # noqa: F401 — re-exported for callers
)
from app.core.config import Settings
from app.core.metrics import AI_FAILURES_TOTAL, ANALYSES_TOTAL
from app.models.analysis import Analysis, FindingRecord
from app.models.configuration import Configuration
from app.schemas.finding import ConfigurationType
from app.services.ai_analysis import AIAnalysisService
from app.services.scoring import calculate_score

logger = logging.getLogger(__name__)


async def run_analysis_pipeline(
    configuration: Configuration,
    session: AsyncSession,
    settings: Settings,
    ai_provider: AIProvider | None = None,
) -> Analysis:
    """Run the full analysis pipeline for a configuration.

    Raises:
        InvalidConfigurationError: if the configuration content cannot be parsed.
            Callers should convert this to HTTP 422.
    """
    from app.ai.factory import get_ai_provider  # local import to avoid circular deps

    config_type = ConfigurationType(configuration.configuration_type)
    analyzer = get_analyzer(config_type)
    # Raises InvalidConfigurationError on malformed content — propagates to caller
    static_findings = analyzer.analyze(configuration.original_content)

    provider = ai_provider or get_ai_provider(settings)
    ai_service = AIAnalysisService(provider)

    analysis = Analysis(
        id=uuid4(),
        configuration_id=configuration.id,
        status="running",
    )
    session.add(analysis)

    ai_findings = []
    error_message = None

    try:
        ai_request = AIAnalysisRequest(
            configuration_type=config_type,
            content=configuration.original_content,
            deterministic_findings=static_findings,
        )
        ai_response = await ai_service.analyze(ai_request)
        ai_findings = list(ai_response.findings)
    except AIProviderError as exc:
        logger.warning(
            "AI analysis failed for configuration %s; using static findings only: %s",
            configuration.id,
            exc,
        )
        error_message = f"AI analysis unavailable: {exc}"
        AI_FAILURES_TOTAL.inc()

    overall_score = calculate_score(
        [f.severity.value for f in static_findings] + [f.severity.value for f in ai_findings]
    )

    for f in static_findings:
        session.add(
            FindingRecord(
                id=uuid4(),
                analysis_id=analysis.id,
                rule_id=f.rule_id,
                category=f.category.value,
                severity=f.severity.value,
                title=f.title,
                description=f.description,
                recommendation=f.recommendation,
                line_number=f.line_number,
                evidence=f.evidence,
                source="deterministic",
                confidence=None,
            )
        )

    for f in ai_findings:
        session.add(
            FindingRecord(
                id=uuid4(),
                analysis_id=analysis.id,
                rule_id=None,
                category=f.category.value,
                severity=f.severity.value,
                title=f.title,
                description=f.description,
                recommendation=f.recommendation,
                line_number=f.line_number,
                evidence=f.evidence,
                source="ai",
                confidence=f.confidence,
            )
        )

    analysis.status = "completed"
    analysis.overall_score = overall_score
    analysis.completed_at = datetime.now(UTC)
    analysis.error_message = error_message

    await session.commit()

    result = await session.execute(
        select(Analysis).where(Analysis.id == analysis.id).options(selectinload(Analysis.findings))
    )
    loaded = result.scalar_one()

    logger.info(
        "Analysis %s completed: score=%.1f, static=%d, ai=%d",
        analysis.id,
        overall_score,
        len(static_findings),
        len(ai_findings),
    )
    ANALYSES_TOTAL.inc()
    return loaded
