"""REST endpoints for analysis resources."""

import json
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analyzers.factory import RULE_VERSIONS
from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.models.analysis import Analysis
from app.models.configuration import Configuration
from app.models.user import User
from app.schemas.analysis import AnalysisResponse
from app.services.analyses import get_analysis, list_analyses
from app.services.sarif import analysis_to_sarif
from app.services.score_explanation import explain_score

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.get("/rule-versions", tags=["analyses"])
async def get_rule_versions() -> dict[str, str]:
    """Return the current rule version string for every configuration type.
    Clients compare a stored analysis.rule_version against these to detect staleness."""
    return {ct.value: version for ct, version in RULE_VERSIONS.items()}


@router.get("/shared/{share_token}", response_model=AnalysisResponse, tags=["share"])
async def get_shared_analysis(
    share_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> AnalysisResponse:
    result = await session.execute(
        select(Analysis)
        .where(Analysis.share_token == share_token)
        .options(selectinload(Analysis.findings))
    )
    analysis = result.scalar_one_or_none()
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared report not found")
    return analysis  # type: ignore[return-value]


@router.get("/", response_model=list[AnalysisResponse])
async def list_all(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[AnalysisResponse]:
    return await list_analyses(session, current_user.id)  # type: ignore[return-value]


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_one(
    analysis_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> AnalysisResponse:
    analysis = await get_analysis(session, analysis_id, current_user.id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return analysis  # type: ignore[return-value]


@router.post("/{analysis_id}/share", response_model=AnalysisResponse)
async def share_analysis(
    analysis_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> AnalysisResponse:
    analysis = await get_analysis(session, analysis_id, current_user.id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    if analysis.share_token is None:
        analysis.share_token = str(uuid4())
        await session.commit()
        await session.refresh(analysis)
    return analysis  # type: ignore[return-value]


@router.delete("/{analysis_id}/share", status_code=status.HTTP_204_NO_CONTENT)
async def unshare_analysis(
    analysis_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    analysis = await get_analysis(session, analysis_id, current_user.id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    analysis.share_token = None
    await session.commit()


@router.get("/{analysis_id}/explain-score")
async def explain_analysis_score(
    analysis_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    analysis = await get_analysis(session, analysis_id, current_user.id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    if analysis.overall_score is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Analysis not yet complete")
    text = await explain_score(analysis, settings)
    return {"explanation": text}


@router.get("/{analysis_id}/sarif")
async def export_sarif(
    analysis_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    analysis = await get_analysis(session, analysis_id, current_user.id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    sarif_doc = analysis_to_sarif(analysis)
    filename = f"analysis-{analysis_id}.sarif"
    return Response(
        content=json.dumps(sarif_doc, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
