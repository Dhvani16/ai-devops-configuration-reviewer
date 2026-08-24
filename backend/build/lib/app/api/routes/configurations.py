"""REST endpoints for configuration resources."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import AIProvider
from app.analyzers.interface import InvalidConfigurationError
from app.api.deps import get_ai_provider_dep, get_current_user
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.analysis import AnalysisResponse
from app.schemas.configuration import (
    ConfigurationCreate,
    ConfigurationDetailResponse,
    ConfigurationResponse,
)
from app.services.analysis_pipeline import run_analysis_pipeline
from app.services.configurations import (
    create_configuration,
    delete_configuration,
    get_configuration,
    list_configurations,
)

router = APIRouter(prefix="/configurations", tags=["configurations"])


@router.post("/", response_model=ConfigurationDetailResponse, status_code=status.HTTP_201_CREATED)
async def create(
    payload: ConfigurationCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ConfigurationDetailResponse:
    return await create_configuration(session, current_user.id, payload)  # type: ignore[return-value]


@router.get("/", response_model=list[ConfigurationResponse])
async def list_all(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ConfigurationResponse]:
    return await list_configurations(session, current_user.id)  # type: ignore[return-value]


@router.get("/{configuration_id}", response_model=ConfigurationDetailResponse)
async def get_one(
    configuration_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ConfigurationDetailResponse:
    config = await get_configuration(session, configuration_id, current_user.id)
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")
    return config  # type: ignore[return-value]


@router.delete("/{configuration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    configuration_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    deleted = await delete_configuration(session, configuration_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")


@router.post("/{configuration_id}/analyze", response_model=AnalysisResponse)
async def analyze(
    configuration_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    ai_provider: AIProvider = Depends(get_ai_provider_dep),
) -> AnalysisResponse:
    config = await get_configuration(session, configuration_id, current_user.id)
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")
    try:
        return await run_analysis_pipeline(config, session, settings, ai_provider=ai_provider)  # type: ignore[return-value]
    except InvalidConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid configuration content: {exc}",
        ) from exc
