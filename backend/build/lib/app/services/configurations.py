"""CRUD operations for Configuration resources."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.configuration import Configuration
from app.schemas.configuration import ConfigurationCreate


async def create_configuration(
    session: AsyncSession, user_id: UUID, data: ConfigurationCreate
) -> Configuration:
    config = Configuration(
        user_id=user_id,
        name=data.name,
        configuration_type=data.configuration_type.value,
        original_content=data.original_content,
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return config


async def get_configuration(
    session: AsyncSession, config_id: UUID, user_id: UUID
) -> Configuration | None:
    result = await session.execute(
        select(Configuration).where(
            Configuration.id == config_id,
            Configuration.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_configurations(session: AsyncSession, user_id: UUID) -> list[Configuration]:
    result = await session.execute(
        select(Configuration)
        .where(Configuration.user_id == user_id)
        .order_by(Configuration.created_at.desc())
        .limit(100)
    )
    return list(result.scalars().all())


async def delete_configuration(
    session: AsyncSession, config_id: UUID, user_id: UUID
) -> bool:
    config = await get_configuration(session, config_id, user_id)
    if config is None:
        return False
    await session.delete(config)
    await session.commit()
    return True
