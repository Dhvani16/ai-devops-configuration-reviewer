"""Analyzer selection by supported configuration type."""

from app.analyzers.compose import ComposeAnalyzer
from app.analyzers.dockerfile import DockerfileAnalyzer
from app.analyzers.github_actions import GitHubActionsAnalyzer
from app.analyzers.interface import ConfigurationAnalyzer
from app.analyzers.kubernetes import KubernetesAnalyzer
from app.analyzers.terraform import TerraformAnalyzer
from app.schemas.finding import ConfigurationType

# Bump the version string for a config type whenever its rule set changes.
# Any existing analysis with a different rule_version will be auto re-analyzed at startup.
RULE_VERSIONS: dict[ConfigurationType, str] = {
    ConfigurationType.DOCKERFILE: "2026-11-02",
    ConfigurationType.DOCKER_COMPOSE: "2026-11-02",
    ConfigurationType.GITHUB_ACTIONS: "2026-11-02",
    ConfigurationType.KUBERNETES: "2026-11-02",
    ConfigurationType.TERRAFORM: "2026-11-02",
}


def get_rule_version(configuration_type: ConfigurationType) -> str:
    return RULE_VERSIONS[configuration_type]


def get_analyzer(configuration_type: ConfigurationType) -> ConfigurationAnalyzer:
    analyzers: dict[ConfigurationType, ConfigurationAnalyzer] = {
        ConfigurationType.DOCKERFILE: DockerfileAnalyzer(),
        ConfigurationType.DOCKER_COMPOSE: ComposeAnalyzer(),
        ConfigurationType.GITHUB_ACTIONS: GitHubActionsAnalyzer(),
        ConfigurationType.KUBERNETES: KubernetesAnalyzer(),
        ConfigurationType.TERRAFORM: TerraformAnalyzer(),
    }
    return analyzers[configuration_type]
