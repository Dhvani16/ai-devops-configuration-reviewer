"""Common request dependencies."""

from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_ai_provider
from app.ai.provider import AIProvider
from app.core.config import Settings, get_settings
from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> User:
    try:
        user_id: UUID = decode_access_token(token, settings)
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception from None
    user = await session.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user


def get_ai_provider_dep(settings: Settings = Depends(get_settings)) -> AIProvider:
    return get_ai_provider(settings)
