"""Validated contracts shared by deterministic and AI analysis layers."""

from enum import Enum

from pydantic import BaseModel, Field


class ConfigurationType(str, Enum):
    DOCKERFILE = "dockerfile"
    DOCKER_COMPOSE = "docker_compose"
    GITHUB_ACTIONS = "github_actions"


class FindingCategory(str, Enum):
    SECURITY = "security"
    RELIABILITY = "reliability"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"


class FindingSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FindingSource(str, Enum):
    DETERMINISTIC = "deterministic"
    AI = "ai"


class Finding(BaseModel):
    rule_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    category: FindingCategory
    severity: FindingSeverity
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1)
    recommendation: str = Field(min_length=1)
    line_number: int | None = Field(default=None, ge=1)
    evidence: str = Field(min_length=1)
    source: FindingSource = FindingSource.DETERMINISTIC
