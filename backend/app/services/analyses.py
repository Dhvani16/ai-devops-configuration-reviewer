"""Read operations for Analysis resources (write path lives in analysis_pipeline.py)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analysis import Analysis, FindingRecord
from app.models.configuration import Configuration
from app.schemas.analysis import TrendPoint


async def get_analysis(session: AsyncSession, analysis_id: UUID, user_id: UUID) -> Analysis | None:
    result = await session.execute(
        select(Analysis)
        .join(Configuration, Analysis.configuration_id == Configuration.id)
        .where(Analysis.id == analysis_id, Configuration.user_id == user_id)
        .options(selectinload(Analysis.findings))
    )
    return result.scalar_one_or_none()


async def list_analyses(session: AsyncSession, user_id: UUID) -> list[Analysis]:
    result = await session.execute(
        select(Analysis)
        .join(Configuration, Analysis.configuration_id == Configuration.id)
        .where(Configuration.user_id == user_id)
        .order_by(Analysis.created_at.desc())
        .limit(50)
        .options(selectinload(Analysis.findings))
    )
    return list(result.scalars().all())


async def get_trend(
    session: AsyncSession, configuration_id: UUID, user_id: UUID
) -> list[TrendPoint]:
    config_check = await session.execute(
        select(Configuration).where(
            Configuration.id == configuration_id,
            Configuration.user_id == user_id,
        )
    )
    if config_check.scalar_one_or_none() is None:
        return []

    result = await session.execute(
        select(Analysis)
        .where(
            Analysis.configuration_id == configuration_id,
            Analysis.status == "completed",
            Analysis.overall_score.is_not(None),
        )
        .order_by(Analysis.created_at)
        .options(selectinload(Analysis.findings))
        .limit(50)
    )
    analyses = list(result.scalars().all())

    points: list[TrendPoint] = []
    for a in analyses:
        findings: list[FindingRecord] = a.findings
        points.append(
            TrendPoint(
                analysis_id=a.id,
                created_at=a.created_at,
                overall_score=a.overall_score,  # type: ignore[arg-type]
                total=len(findings),
                critical=sum(1 for f in findings if f.severity == "critical"),
                high=sum(1 for f in findings if f.severity == "high"),
                medium=sum(1 for f in findings if f.severity == "medium"),
                low=sum(1 for f in findings if f.severity == "low"),
            )
        )
    return points
