"""REST endpoints for per-finding remediation chat."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.analysis import ChatMessageResponse, ChatSendRequest
from app.services.chat import get_chat_history, get_finding_for_user, send_chat_message

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("/{finding_id}/chat", response_model=list[ChatMessageResponse])
async def list_chat_messages(
    finding_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ChatMessageResponse]:
    finding = await get_finding_for_user(session, finding_id, current_user.id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    return await get_chat_history(session, finding_id)  # type: ignore[return-value]


@router.post(
    "/{finding_id}/chat",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_chat_message(
    finding_id: UUID,
    body: ChatSendRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> ChatMessageResponse:
    finding = await get_finding_for_user(session, finding_id, current_user.id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    return await send_chat_message(session, finding, body.message, settings)  # type: ignore[return-value]
