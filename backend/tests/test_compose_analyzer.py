import pytest

from app.analyzers.compose import ComposeAnalyzer
from app.analyzers.interface import InvalidConfigurationError


@pytest.mark.parametrize(
    ("service", "rule_id"),
    [
        ("privileged: true\n    restart: always", "compose-privileged"),
        ("network_mode: host\n    restart: always", "compose-host-network"),
        ("volumes:\n      - /var/run/docker.sock:/var/run/docker.sock\n    restart: always", "compose-docker-socket"),
        ("image: nginx", "compose-missing-restart"),
        ("cap_add:\n      - ALL\n    restart: always", "compose-all-capabilities"),
        ("user: '0:0'\n    restart: always", "compose-root-user"),
        ("environment:\n      DATABASE_PASSWORD: literal\n    restart: always", "compose-hard-coded-secret"),
    ],
)
def test_compose_rules(service: str, rule_id: str) -> None:
    content = f"services:\n  app:\n    {service}\n"

    findings = ComposeAnalyzer().analyze(content)

    assert rule_id in {finding.rule_id for finding in findings}


def test_compose_rejects_invalid_yaml() -> None:
    with pytest.raises(InvalidConfigurationError):
        ComposeAnalyzer().analyze("services: [")


def test_compose_allows_environment_reference() -> None:
    content = "services:\n  app:\n    restart: always\n    environment:\n      DATABASE_PASSWORD: ${DATABASE_PASSWORD}\n"

    assert ComposeAnalyzer().analyze(content) == []
