"""Application service for provider-neutral AI analysis."""

import logging

from app.ai.provider import AIProvider, AIProviderError
from app.ai.schemas import AIAnalysisRequest, AIAnalysisResponse

logger = logging.getLogger(__name__)


class AIAnalysisService:
    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    async def analyze(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        try:
            return await self._provider.analyze(request)
        except AIProviderError:
            logger.exception(
                "AI analysis failed for configuration type %s", request.configuration_type.value
            )
            raise
