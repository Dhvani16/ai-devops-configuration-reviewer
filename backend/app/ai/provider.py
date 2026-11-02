"""Provider abstraction and safe structured-response parsing."""

import json
from abc import ABC, abstractmethod

from pydantic import ValidationError

from app.ai.schemas import AIAnalysisRequest, AIAnalysisResponse


class AIProviderError(RuntimeError):
    """Raised when an AI provider cannot complete an analysis request."""


class AIResponseValidationError(AIProviderError):
    """Raised when a provider response cannot satisfy the AI response schema."""


class AIProvider(ABC):
    @abstractmethod
    async def analyze(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        """Return schema-validated AI findings without persistence side effects."""


def parse_ai_response(raw_response: str) -> AIAnalysisResponse:
    """Validate JSON, with limited recovery for a fenced JSON response."""
    candidates = [raw_response.strip()]
    if "```" in raw_response:
        candidates.append(raw_response.replace("```json", "").replace("```", "").strip())
    start, end = raw_response.find("{"), raw_response.rfind("}")
    if start >= 0 and end > start:
        candidates.append(raw_response[start : end + 1])

    for candidate in candidates:
        try:
            return AIAnalysisResponse.model_validate(json.loads(candidate))
        except (json.JSONDecodeError, ValidationError):
            continue
    raise AIResponseValidationError("AI provider returned malformed structured output")
