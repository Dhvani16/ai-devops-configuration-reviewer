"""REST endpoints for analysis resources."""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.analysis import AnalysisResponse
from app.services.analyses import get_analysis, list_analyses
from app.services.sarif import analysis_to_sarif

router = APIRouter(prefix="/analyses", tags=["analyses"])


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
