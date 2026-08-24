"""Request/response schemas for analysis resources."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.finding import FindingCategory, FindingSeverity, FindingSource


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

    model_config = {"from_attributes": True}


class AnalysisResponse(BaseModel):
    id: UUID
    configuration_id: UUID
    status: str
    overall_score: float | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    findings: list[FindingResponse] = []

    model_config = {"from_attributes": True}
