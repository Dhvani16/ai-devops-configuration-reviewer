"""Integration tests for the analysis pipeline using MockAIProvider and in-memory SQLite."""

import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai.mock_provider import MockAIProvider
from app.ai.provider import AIProviderError
from app.ai.schemas import AIAnalysisFinding, AIAnalysisResponse
from app.core.config import get_settings
from app.db.base import Base
from app.models.configuration import Configuration
from app.models.user import User
from app.schemas.finding import FindingCategory, FindingSeverity
from app.services.analysis_pipeline import run_analysis_pipeline


def _make_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(setup())
    return engine, factory


def test_pipeline_with_mock_ai() -> None:
    engine, factory = _make_db()

    async def run():
        async with factory() as session:
            user = User(email="pipe@example.com", hashed_password="x")
            session.add(user)
            await session.flush()

            config = Configuration(
                user_id=user.id,
                name="test-dockerfile",
                configuration_type="dockerfile",
                # Missing USER instruction triggers deterministic finding
                original_content="FROM python:3.12\nRUN apt-get install vim\n",
            )
            session.add(config)
            await session.flush()

            ai_finding = AIAnalysisFinding(
                category=FindingCategory.SECURITY,
                severity=FindingSeverity.MEDIUM,
                title="AI-detected issue",
                description="Description of issue",
                recommendation="Fix it",
                evidence="Some evidence",
                confidence=0.9,
            )
            mock_provider = MockAIProvider(AIAnalysisResponse(findings=[ai_finding]))
            settings = get_settings()
            analysis = await run_analysis_pipeline(
                config, session, settings, ai_provider=mock_provider
            )
            return analysis, mock_provider.requests

    analysis, requests = asyncio.run(run())
    asyncio.run(engine.dispose())

    assert analysis.status == "completed"
    assert analysis.overall_score is not None
    assert analysis.overall_score < 100.0

    sources = {f.source for f in analysis.findings}
    assert "deterministic" in sources
    assert "ai" in sources

    assert len(requests) == 1  # AI was called exactly once


def test_pipeline_continues_when_ai_fails() -> None:
    engine, factory = _make_db()

    class FailingProvider:
        async def analyze(self, request):
            raise AIProviderError("API unavailable")

    async def run():
        async with factory() as session:
            user = User(email="pipe2@example.com", hashed_password="x")
            session.add(user)
            await session.flush()

            config = Configuration(
                user_id=user.id,
                name="compose",
                configuration_type="docker_compose",
                original_content=(
                    "version: '3'\nservices:\n  app:\n    image: nginx\n    privileged: true\n"
                ),
            )
            session.add(config)
            await session.flush()

            settings = get_settings()
            return await run_analysis_pipeline(
                config, session, settings, ai_provider=FailingProvider()
            )

    analysis = asyncio.run(run())
    asyncio.run(engine.dispose())

    assert analysis.status == "completed"
    assert analysis.error_message is not None
    assert "AI analysis unavailable" in analysis.error_message
    assert any(f.source == "deterministic" for f in analysis.findings)
    assert all(f.source == "deterministic" for f in analysis.findings)


def test_pipeline_raises_on_invalid_config() -> None:
    engine, factory = _make_db()

    async def run():
        async with factory() as session:
            user = User(email="pipe3@example.com", hashed_password="x")
            session.add(user)
            await session.flush()

            config = Configuration(
                user_id=user.id,
                name="bad-yaml",
                configuration_type="docker_compose",
                original_content="this: is: not: valid: yaml: [[[",
            )
            session.add(config)
            await session.flush()

            mock_provider = MockAIProvider()
            settings = get_settings()
            await run_analysis_pipeline(
                config, session, settings, ai_provider=mock_provider
            )

    with pytest.raises(Exception):  # InvalidConfigurationError
        asyncio.run(run())

    asyncio.run(engine.dispose())
