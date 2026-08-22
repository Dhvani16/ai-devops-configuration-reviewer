"""Pydantic contracts for AI analysis requests and structured responses."""

from pydantic import BaseModel, Field

from app.schemas.finding import ConfigurationType, Finding, FindingCategory, FindingSeverity


class AIAnalysisRequest(BaseModel):
    configuration_type: ConfigurationType
    content: str = Field(min_length=1)
    deterministic_findings: list[Finding] = Field(default_factory=list)


class AIAnalysisFinding(BaseModel):
    category: FindingCategory
    severity: FindingSeverity
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1)
    recommendation: str = Field(min_length=1)
    line_number: int | None = Field(default=None, ge=1)
    evidence: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class AIAnalysisResponse(BaseModel):
    findings: list[AIAnalysisFinding] = Field(default_factory=list, max_length=20)
