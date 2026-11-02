"""Request/response schemas for configuration resources."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.finding import ConfigurationType


class ConfigurationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    configuration_type: ConfigurationType
    original_content: str = Field(min_length=1, max_length=100_000)


class ConfigurationResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    configuration_type: ConfigurationType
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConfigurationDetailResponse(ConfigurationResponse):
    original_content: str
