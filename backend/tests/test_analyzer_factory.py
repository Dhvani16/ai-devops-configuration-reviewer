import pytest

from app.analyzers import get_analyzer
from app.analyzers.compose import ComposeAnalyzer
from app.analyzers.dockerfile import DockerfileAnalyzer
from app.analyzers.github_actions import GitHubActionsAnalyzer
from app.schemas.finding import ConfigurationType


@pytest.mark.parametrize(
    ("configuration_type", "analyzer_class"),
    [
        (ConfigurationType.DOCKERFILE, DockerfileAnalyzer),
        (ConfigurationType.DOCKER_COMPOSE, ComposeAnalyzer),
        (ConfigurationType.GITHUB_ACTIONS, GitHubActionsAnalyzer),
    ],
)
def test_factory_returns_supported_analyzer(
    configuration_type: ConfigurationType, analyzer_class: type
) -> None:
    assert isinstance(get_analyzer(configuration_type), analyzer_class)
