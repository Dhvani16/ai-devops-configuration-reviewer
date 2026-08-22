import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from app.ai.mock_provider import MockAIProvider
from app.ai.ollama_provider import OllamaProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.provider import AIProviderError, AIResponseValidationError, parse_ai_response
from app.ai.schemas import AIAnalysisFinding, AIAnalysisRequest, AIAnalysisResponse
from app.core.config import Settings
from app.schemas.finding import ConfigurationType, FindingCategory, FindingSeverity
from app.services.ai_analysis import AIAnalysisService


def settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "sqlite+aiosqlite:///./test.db",
        "secret_key": "test-secret-key-that-is-longer-than-thirty-two-characters",
        "openai_api_key": "test-key",
    }
    values.update(overrides)
    return Settings.model_validate(values)


def valid_response() -> AIAnalysisResponse:
    return AIAnalysisResponse(
        findings=[
            AIAnalysisFinding(
                category=FindingCategory.SECURITY,
                severity=FindingSeverity.HIGH,
                title="Example issue",
                description="The configuration grants more access than necessary.",
                recommendation="Limit the access to the required scope.",
                line_number=3,
                evidence="permissions: write-all",
                confidence=0.92,
            )
        ]
    )


def request() -> AIAnalysisRequest:
    return AIAnalysisRequest(configuration_type=ConfigurationType.GITHUB_ACTIONS, content="on: push")


def test_parse_ai_response_recovers_fenced_json() -> None:
    raw = f"```json\n{valid_response().model_dump_json()}\n```"

    assert parse_ai_response(raw) == valid_response()


def test_parse_ai_response_rejects_invalid_schema() -> None:
    raw = json.dumps({"findings": [{"title": "incomplete"}]})

    with pytest.raises(AIResponseValidationError):
        parse_ai_response(raw)


def test_mock_provider_is_used_without_network() -> None:
    provider = MockAIProvider(valid_response())

    response = asyncio.run(AIAnalysisService(provider).analyze(request()))

    assert response == valid_response()
    assert provider.requests == [request()]


def test_openai_provider_requests_strict_structured_output() -> None:
    captured: dict[str, object] = {}

    class FakeResponses:
        async def create(self, **kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(output_text=valid_response().model_dump_json())

    client = SimpleNamespace(responses=FakeResponses())
    response = asyncio.run(OpenAIProvider(settings(), client=client).analyze(request()))

    assert response == valid_response()
    assert captured["store"] is False
    text = captured["text"]
    assert isinstance(text, dict)
    assert text["format"]["strict"] is True


def test_openai_provider_enforces_input_limit() -> None:
    provider = OpenAIProvider(settings(ai_max_input_characters=10), client=SimpleNamespace())

    with pytest.raises(AIProviderError, match="input limit"):
        asyncio.run(provider.analyze(request()))


def test_ollama_provider_validates_structured_output() -> None:
    async def handler(received: httpx.Request) -> httpx.Response:
        assert received.url.path == "/api/generate"
        return httpx.Response(200, json={"response": valid_response().model_dump_json()})

    async def run() -> AIAnalysisResponse:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            return await OllamaProvider(settings(ai_provider="ollama"), client=client).analyze(request())
        finally:
            await client.aclose()

    assert asyncio.run(run()) == valid_response()
