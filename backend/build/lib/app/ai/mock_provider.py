"""Deterministic provider used by automated tests."""

from app.ai.provider import AIProvider
from app.ai.schemas import AIAnalysisRequest, AIAnalysisResponse


class MockAIProvider(AIProvider):
    def __init__(self, response: AIAnalysisResponse | None = None) -> None:
        self.response = response or AIAnalysisResponse()
        self.requests: list[AIAnalysisRequest] = []

    async def analyze(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        self.requests.append(request)
        return self.response
