"""Request/response schemas for analysis resources."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.finding import FindingCategory, FindingSeverity, FindingSource


class ChatMessageResponse(BaseModel):
    id: UUID
    finding_id: UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSendRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class FindingResponse(BaseModel):
    id: UUID
    rule_id: str | None
    category: FindingCategory
    severity: FindingSeverity
    title: str
    description: str
    recommendation: str
    line_number: int | None
    evidence: str
    source: FindingSource
    confidence: float | None
    fix_suggestion: str | None

    model_config = {"from_attributes": True}


class TrendPoint(BaseModel):
    analysis_id: UUID
    created_at: datetime
    overall_score: float
    total: int
    critical: int
    high: int
    medium: int
    low: int

    model_config = {"from_attributes": False}


class AnalysisResponse(BaseModel):
    id: UUID
    configuration_id: UUID
    status: str
    overall_score: float | None
    rule_version: str | None
    share_token: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    findings: list[FindingResponse] = []

    model_config = {"from_attributes": True}
