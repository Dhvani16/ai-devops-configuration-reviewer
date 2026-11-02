"""Rule-based Docker Compose analysis."""

import re
from typing import Any

import yaml

from app.analyzers.interface import ConfigurationAnalyzer, InvalidConfigurationError
from app.analyzers.utils import find_line_number
from app.schemas.finding import ConfigurationType, Finding, FindingCategory, FindingSeverity

SECRET_PATTERN = re.compile(r"(password|secret|token|api[_-]?key|access[_-]?key)", re.IGNORECASE)


class ComposeAnalyzer(ConfigurationAnalyzer):
    configuration_type = ConfigurationType.DOCKER_COMPOSE

    def analyze(self, content: str) -> list[Finding]:
        document = _load_compose(content)
        services = document.get("services")
        if not isinstance(services, dict):
            raise InvalidConfigurationError(
                "Docker Compose configuration must contain a services mapping"
            )

        findings: list[Finding] = []
        for service_name, service in services.items():
            if not isinstance(service, dict):
                raise InvalidConfigurationError(f"Service '{service_name}' must be a mapping")
            findings.extend(self._analyze_service(str(service_name), service, content))
        return findings

    def _analyze_service(self, name: str, service: dict[str, Any], content: str) -> list[Finding]:
        findings: list[Finding] = []
        if service.get("privileged") is True:
            findings.append(
                _finding(
                    "compose-privileged",
                    FindingSeverity.CRITICAL,
                    "Privileged container",
                    "privileged",
                )
            )
        if service.get("network_mode") == "host":
            findings.append(
                _finding(
                    "compose-host-network",
                    FindingSeverity.HIGH,
                    "Host network enabled",
                    "network_mode",
                )
            )
        if _contains_docker_socket(service.get("volumes")):
            findings.append(
                _finding(
                    "compose-docker-socket",
                    FindingSeverity.CRITICAL,
                    "Docker socket mounted",
                    "docker.sock",
                )
            )
        if "restart" not in service:
            findings.append(
                _finding(
                    "compose-missing-restart", FindingSeverity.MEDIUM, "No restart policy", name
                )
            )
        if _has_all_capabilities(service.get("cap_add")):
            findings.append(
                _finding(
                    "compose-all-capabilities",
                    FindingSeverity.HIGH,
                    "All Linux capabilities added",
                    "cap_add",
                )
            )
        if str(service.get("user", "")).strip().lower() in {"root", "0", "0:0"}:
            findings.append(
                _finding(
                    "compose-root-user",
                    FindingSeverity.HIGH,
                    "Service explicitly runs as root",
                    "user",
                )
            )
        for key, value in _environment_values(service.get("environment")):
            if SECRET_PATTERN.search(key) and _is_hard_coded(value):
                findings.append(
                    _finding(
                        "compose-hard-coded-secret",
                        FindingSeverity.HIGH,
                        "Hard-coded secret in environment",
                        key,
                    )
                )
        return [
            finding.model_copy(
                update={"line_number": find_line_number(content, re.escape(finding.evidence))}
            )
            for finding in findings
        ]


def _load_compose(content: str) -> dict[str, Any]:
    try:
        document = yaml.safe_load(content)
    except yaml.YAMLError as error:
        raise InvalidConfigurationError("Docker Compose YAML is invalid") from error
    if not isinstance(document, dict):
        raise InvalidConfigurationError("Docker Compose configuration must be a YAML mapping")
    return document


def _contains_docker_socket(volumes: Any) -> bool:
    return isinstance(volumes, list) and any(
        "/var/run/docker.sock" in str(volume) for volume in volumes
    )


def _has_all_capabilities(capabilities: Any) -> bool:
    return isinstance(capabilities, list) and any(
        str(item).upper() == "ALL" for item in capabilities
    )


def _environment_values(environment: Any) -> list[tuple[str, str]]:
    if isinstance(environment, dict):
        return [(str(key), str(value)) for key, value in environment.items()]
    if isinstance(environment, list):
        return [
            tuple(item.split("=", 1))
            for item in environment
            if isinstance(item, str) and "=" in item
        ]
    return []


def _is_hard_coded(value: str) -> bool:
    return bool(value.strip()) and not value.strip().startswith("${")


def _finding(rule_id: str, severity: FindingSeverity, title: str, evidence: str) -> Finding:
    descriptions = {
        "compose-privileged": "Privileged mode grants a container near-host-level access.",
        "compose-host-network": "Host networking removes network isolation for this service.",
        "compose-docker-socket": "A Docker socket mount can allow control of the host Docker daemon.",
        "compose-missing-restart": "A service without a restart policy may not recover after a failure.",
        "compose-all-capabilities": "Adding all capabilities weakens container isolation.",
        "compose-root-user": "Running as root increases the impact of a container compromise.",
        "compose-hard-coded-secret": "A literal secret in Compose can be committed to source control.",
    }
    recommendations = {
        "compose-privileged": "Remove privileged mode and grant only the narrowly required capability.",
        "compose-host-network": "Use an isolated Compose network unless host networking is essential.",
        "compose-docker-socket": "Avoid mounting the Docker socket; use a narrowly scoped integration instead.",
        "compose-missing-restart": "Set a suitable restart policy, such as unless-stopped or on-failure.",
        "compose-all-capabilities": "Remove cap_add: ALL and add only documented required capabilities.",
        "compose-root-user": "Run the service as a dedicated non-root user.",
        "compose-hard-coded-secret": "Use environment injection or a secret manager rather than a literal value.",
    }
    category = (
        FindingCategory.RELIABILITY
        if rule_id == "compose-missing-restart"
        else FindingCategory.SECURITY
    )
    return Finding(
        rule_id=rule_id,
        category=category,
        severity=severity,
        title=title,
        description=descriptions[rule_id],
        recommendation=recommendations[rule_id],
        line_number=None,
        evidence=evidence,
    )
