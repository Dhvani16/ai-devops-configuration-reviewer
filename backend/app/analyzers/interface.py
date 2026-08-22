"""Base interface for deterministic configuration analyzers."""

from abc import ABC, abstractmethod

from app.schemas.finding import ConfigurationType, Finding


class InvalidConfigurationError(ValueError):
    """Raised when submitted configuration cannot be parsed safely."""


class ConfigurationAnalyzer(ABC):
    configuration_type: ConfigurationType

    @abstractmethod
    def analyze(self, content: str) -> list[Finding]:
        """Return deterministic, schema-validated findings for configuration text."""
