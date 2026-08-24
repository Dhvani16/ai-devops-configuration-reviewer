"""OpenAI Responses API implementation of the AI provider contract."""

from typing import Any

from openai import APIError, AsyncOpenAI

from app.ai.prompts.configuration_analysis import SYSTEM_PROMPT, build_analysis_input
from app.ai.provider import AIProvider, AIProviderError, parse_ai_response
from app.ai.schemas import AIAnalysisRequest, AIAnalysisResponse
from app.core.config import Settings


class OpenAIProvider(AIProvider):
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        if not settings.openai_api_key and client is None:
            raise AIProviderError("OPENAI_API_KEY is required when AI_PROVIDER=openai")
        self._client = client or AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model
        self._max_input_characters = settings.ai_max_input_characters
        self._max_output_tokens = settings.ai_max_output_tokens

    async def analyze(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        input_text = build_analysis_input(request)
        if len(input_text) > self._max_input_characters:
            raise AIProviderError("Configuration exceeds the configured AI input limit")
        try:
            response = await self._client.responses.create(
                model=self._model,
                instructions=SYSTEM_PROMPT,
                input=input_text,
                max_output_tokens=self._max_output_tokens,
                store=False,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "configuration_analysis",
                        "schema": AIAnalysisResponse.model_json_schema(),
                        "strict": True,
                    }
                },
            )
        except APIError as error:
            raise AIProviderError("OpenAI analysis request failed") from error
        return parse_ai_response(response.output_text)
