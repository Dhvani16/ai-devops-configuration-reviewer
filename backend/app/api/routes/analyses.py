"""REST endpoints for analysis resources."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.analysis import AnalysisResponse
from app.services.analyses import get_analysis, list_analyses

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
