"""Optional local Ollama implementation of the AI provider contract."""

from typing import Any

import httpx

from app.ai.prompts.configuration_analysis import SYSTEM_PROMPT, build_analysis_input
from app.ai.provider import AIProvider, AIProviderError, parse_ai_response
from app.ai.schemas import AIAnalysisRequest, AIAnalysisResponse
from app.core.config import Settings


class OllamaProvider(AIProvider):
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        self._max_input_characters = settings.ai_max_input_characters
        self._client = client

    async def analyze(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        prompt = f"{SYSTEM_PROMPT}\n\n{build_analysis_input(request)}"
        if len(prompt) > self._max_input_characters:
            raise AIProviderError("Configuration exceeds the configured AI input limit")
        payload = {
            "model": self._model,
            "prompt": prompt,
            "format": AIAnalysisResponse.model_json_schema(),
            "stream": False,
        }
        try:
            if self._client is not None:
                response = await self._client.post(f"{self._base_url}/api/generate", json=payload)
            else:
                async with httpx.AsyncClient(timeout=60) as client:
                    response = await client.post(f"{self._base_url}/api/generate", json=payload)
            response.raise_for_status()
            body: dict[str, Any] = response.json()
            output = body.get("response")
            if not isinstance(output, str):
                raise AIProviderError("Ollama returned no text response")
        except httpx.HTTPError as error:
            raise AIProviderError("Ollama analysis request failed") from error
        return parse_ai_response(output)
