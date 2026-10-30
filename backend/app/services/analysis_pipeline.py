"""Analysis pipeline: static analysis → AI analysis → risk scoring → DB persistence.

Public API
----------
run_analysis_pipeline      – synchronous end-to-end (used by tests and legacy callers)
create_pending_analysis    – stage 1: validate config, persist static findings, return pending Analysis
complete_analysis_async    – stage 2: AI call, score, mark completed (runs in BackgroundTasks)
"""

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

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
from app.schemas.finding import ConfigurationType, Finding
from app.services.ai_analysis import AIAnalysisService
from app.services.notifications import notify_analysis_complete
from app.services.scoring import calculate_score

logger = logging.getLogger(__name__)


# ─── internal helpers ────────────────────────────────────────────────────────

def _run_static(configuration: Configuration) -> list[Finding]:
    """Run deterministic analysis. Raises InvalidConfigurationError on bad content."""
    config_type = ConfigurationType(configuration.configuration_type)
    return get_analyzer(config_type).analyze(configuration.original_content)


def _finding_record(analysis_id: UUID, finding: Finding, source: str) -> FindingRecord:
    return FindingRecord(
        id=uuid4(),
        analysis_id=analysis_id,
        rule_id=finding.rule_id,
        category=finding.category.value,
        severity=finding.severity.value,
        title=finding.title,
        description=finding.description,
        recommendation=finding.recommendation,
        line_number=finding.line_number,
        evidence=finding.evidence,
        source=source,
        confidence=None,
    )


async def _persist_static_findings(
    analysis: Analysis, static_findings: list[Finding], session: AsyncSession
) -> None:
    for f in static_findings:
        session.add(_finding_record(analysis.id, f, "deterministic"))


async def _run_ai_and_finalize(
    analysis: Analysis,
    configuration: Configuration,
    static_findings: list[Finding],
    session: AsyncSession,
    settings: Settings,
    ai_provider: AIProvider | None,
) -> None:
    """Run AI analysis, persist AI findings, calculate score, mark analysis completed."""
    from app.ai.factory import get_ai_provider  # local import avoids circular deps

    provider = ai_provider or get_ai_provider(settings)
    ai_service = AIAnalysisService(provider)

    ai_findings = []
    error_message = None

    try:
        ai_request = AIAnalysisRequest(
            configuration_type=ConfigurationType(configuration.configuration_type),
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

    overall_score = calculate_score(
        [f.severity.value for f in static_findings] + [f.severity.value for f in ai_findings]
    )

    analysis.status = "completed"
    analysis.overall_score = overall_score
    analysis.completed_at = datetime.now(UTC)
    analysis.error_message = error_message

    await session.commit()

    logger.info(
        "Analysis %s completed: score=%.1f, static=%d, ai=%d",
        analysis.id,
        overall_score,
        len(static_findings),
        len(ai_findings),
    )
    ANALYSES_TOTAL.inc()

    await notify_analysis_complete(
        analysis_id=str(analysis.id),
        configuration_name=configuration.name,
        configuration_type=configuration.configuration_type,
        overall_score=overall_score,
        finding_count=len(static_findings) + len(ai_findings),
        webhook_url=settings.slack_webhook_url,
    )


# ─── public API ──────────────────────────────────────────────────────────────

async def run_analysis_pipeline(
    configuration: Configuration,
    session: AsyncSession,
    settings: Settings,
    ai_provider: AIProvider | None = None,
) -> Analysis:
    """Run the full pipeline synchronously and return a completed Analysis.

    Used by tests and any caller that wants a blocking, end-to-end result.

    Raises:
        InvalidConfigurationError: if the configuration content cannot be parsed.
    """
    static_findings = _run_static(configuration)

    analysis = Analysis(
        id=uuid4(),
        configuration_id=configuration.id,
        status="running",
    )
    session.add(analysis)
    await _persist_static_findings(analysis, static_findings, session)
    await _run_ai_and_finalize(analysis, configuration, static_findings, session, settings, ai_provider)

    result = await session.execute(
        select(Analysis).where(Analysis.id == analysis.id).options(selectinload(Analysis.findings))
    )
    return result.scalar_one()


async def create_pending_analysis(
    configuration: Configuration,
    session: AsyncSession,
) -> tuple[Analysis, list[Finding]]:
    """Stage 1 — synchronous fast path.

    Validates the configuration (raises InvalidConfigurationError on bad content),
    persists static findings, and returns a 'pending' Analysis row immediately.
    The caller is responsible for scheduling complete_analysis_async as a background task.
    """
    static_findings = _run_static(configuration)

    analysis = Analysis(
        id=uuid4(),
        configuration_id=configuration.id,
        status="pending",
    )
    session.add(analysis)
    await _persist_static_findings(analysis, static_findings, session)
    await session.commit()

    # Reload with findings so the caller can serialise the response immediately
    result = await session.execute(
        select(Analysis).where(Analysis.id == analysis.id).options(selectinload(Analysis.findings))
    )
    analysis = result.scalar_one()

    logger.info(
        "Analysis %s created (pending) for configuration %s with %d static findings",
        analysis.id,
        configuration.id,
        len(static_findings),
    )
    return analysis, static_findings


async def complete_analysis_async(
    analysis_id: UUID,
    configuration_id: UUID,
    static_findings: list[Finding],
    settings: Settings,
    ai_provider: AIProvider | None = None,
) -> None:
    """Stage 2 — intended to run via FastAPI BackgroundTasks.

    Opens its own DB session (the request session is closed by the time this runs),
    runs AI analysis, persists AI findings, calculates score, and marks the analysis
    as 'completed' (or 'completed' with an error_message if AI fails).
    """
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        analysis_result = await session.execute(
            select(Analysis).where(Analysis.id == analysis_id)
        )
        analysis = analysis_result.scalar_one()

        config_result = await session.execute(
            select(Configuration).where(Configuration.id == configuration_id)
        )
        configuration = config_result.scalar_one()

        await _run_ai_and_finalize(
            analysis, configuration, static_findings, session, settings, ai_provider
        )
