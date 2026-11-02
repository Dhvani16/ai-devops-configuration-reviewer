"""AI provider selection from validated application settings."""

from app.ai.ollama_provider import OllamaProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.provider import AIProvider
from app.core.config import Settings, get_settings


def get_ai_provider(settings: Settings | None = None) -> AIProvider:
    active_settings = settings or get_settings()
    if active_settings.ai_provider == "ollama":
        return OllamaProvider(active_settings)
    return OpenAIProvider(active_settings)
