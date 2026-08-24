"""Read operations for Analysis resources (write path lives in analysis_pipeline.py)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analysis import Analysis
from app.models.configuration import Configuration


async def get_analysis(
    session: AsyncSession, analysis_id: UUID, user_id: UUID
) -> Analysis | None:
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
