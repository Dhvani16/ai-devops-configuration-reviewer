"""Analyzer selection by supported configuration type."""

from app.analyzers.compose import ComposeAnalyzer
from app.analyzers.dockerfile import DockerfileAnalyzer
from app.analyzers.github_actions import GitHubActionsAnalyzer
from app.analyzers.interface import ConfigurationAnalyzer
from app.analyzers.kubernetes import KubernetesAnalyzer
from app.analyzers.terraform import TerraformAnalyzer
from app.schemas.finding import ConfigurationType


def get_analyzer(configuration_type: ConfigurationType) -> ConfigurationAnalyzer:
    analyzers: dict[ConfigurationType, ConfigurationAnalyzer] = {
        ConfigurationType.DOCKERFILE: DockerfileAnalyzer(),
        ConfigurationType.DOCKER_COMPOSE: ComposeAnalyzer(),
        ConfigurationType.GITHUB_ACTIONS: GitHubActionsAnalyzer(),
        ConfigurationType.KUBERNETES: KubernetesAnalyzer(),
        ConfigurationType.TERRAFORM: TerraformAnalyzer(),
    }
    return analyzers[configuration_type]
