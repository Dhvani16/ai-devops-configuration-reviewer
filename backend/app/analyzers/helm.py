"""Rule-based Helm chart analysis.

Accepts values.yaml, template files, or a combined paste of chart files.
Uses regex throughout because Go template syntax ({{ }}) makes templates
invalid YAML — the same approach as the Terraform analyzer.
"""

import re

from app.analyzers.interface import ConfigurationAnalyzer, InvalidConfigurationError
from app.schemas.finding import ConfigurationType, Finding, FindingCategory, FindingSeverity

# ─── compiled patterns ────────────────────────────────────────────────────────

# Secrets: plain (non-templated) string values for sensitive keys
_SECRET_LINE = re.compile(
    r'(?im)^\s*(?P<key>password|secretkey|secret_key|api_?key|token|auth_?token|private_?key)'
    r'\s*:\s*(?P<val>"[^"]{3,}"|\'[^\']{3,}\'|[^\s{}\[\]#\n][^\n]*)',
)
_TEMPLATE_VAL = re.compile(r'\{\{')

_PRIVILEGED = re.compile(r'\bprivileged\s*:\s*true\b')
_HOST_NETWORK = re.compile(r'\bhostNetwork\s*:\s*true\b')
_RUN_AS_ROOT = re.compile(r'\brunAsUser\s*:\s*0\b')
_RUN_AS_NON_ROOT_FALSE = re.compile(r'\brunAsNonRoot\s*:\s*false\b')
_DEBUG_MODE = re.compile(r'(?i)\bdebug(?:Mode|Enabled)?\s*:\s*true\b')
_DEFAULT_CREDS = re.compile(
    r'(?im)^\s*(username|user)\s*:\s*(admin|root|administrator)\s*$'
)
_INSECURE_REGISTRY = re.compile(r'repository\s*:\s*["\']?http://')
_HAS_CONTAINERS = re.compile(r'\bcontainers\s*:')
_HAS_LIMITS = re.compile(r'\blimits\s*:')
_HAS_READINESS = re.compile(r'\breadinessProbe\s*:')
_IMAGE_PULL_ALWAYS = re.compile(r'\bpullPolicy\s*:\s*Always\b')
_HELM_CONTENT = re.compile(r'[:\{\}]')  # minimal marker — YAML or Go template


class HelmAnalyzer(ConfigurationAnalyzer):
    configuration_type = ConfigurationType.HELM

    def analyze(self, content: str) -> list[Finding]:
        self._validate(content)
        findings: list[Finding] = []
        findings.extend(_check_hardcoded_secrets(content))
        findings.extend(_check_privileged(content))
        findings.extend(_check_host_network(content))
        findings.extend(_check_root_user(content))
        findings.extend(_check_debug_mode(content))
        findings.extend(_check_default_credentials(content))
        findings.extend(_check_insecure_registry(content))
        findings.extend(_check_missing_resource_limits(content))
        findings.extend(_check_missing_readiness_probe(content))
        return findings

    def _validate(self, content: str) -> None:
        if not content or not content.strip():
            raise InvalidConfigurationError("Helm chart content is empty")
        if not _HELM_CONTENT.search(content):
            raise InvalidConfigurationError(
                "Content does not appear to be a Helm values file or template"
            )


# ─── rule implementations ─────────────────────────────────────────────────────

def _check_hardcoded_secrets(content: str) -> list[Finding]:
    findings = []
    for m in _SECRET_LINE.finditer(content):
        val = m.group("val").strip()
        if _TEMPLATE_VAL.search(val):
            continue  # value is a Go template expression — safe
        if val.strip('"\'') in {"", "changeme", "change-me", "todo", "xxx", "null", "~"}:
            continue  # obviously-placeholder values are skipped
        findings.append(_finding(
            "helm-hardcoded-secret",
            FindingSeverity.CRITICAL,
            FindingCategory.SECURITY,
            "Hardcoded secret in Helm values",
            f"The field '{m.group('key')}' contains a plain-text secret rather than a "
            "Helm secret manager reference or an empty default.",
            "Set the value to an empty string or reference an external secret (e.g. "
            "Sealed Secrets, External Secrets Operator, or Vault Agent).",
            f"{m.group('key')}: <redacted>",
        ))
    return findings


def _check_privileged(content: str) -> list[Finding]:
    if not _PRIVILEGED.search(content):
        return []
    return [_finding(
        "helm-privileged-container",
        FindingSeverity.CRITICAL,
        FindingCategory.SECURITY,
        "Template enables privileged containers",
        "The chart sets privileged: true, granting containers near-host-level access.",
        "Remove privileged mode; grant only specific Linux capabilities if needed.",
        "privileged: true",
    )]


def _check_host_network(content: str) -> list[Finding]:
    if not _HOST_NETWORK.search(content):
        return []
    return [_finding(
        "helm-host-network",
        FindingSeverity.HIGH,
        FindingCategory.SECURITY,
        "Template enables host network",
        "hostNetwork: true removes network isolation between the pod and the node.",
        "Remove hostNetwork; expose ports via a Kubernetes Service instead.",
        "hostNetwork: true",
    )]


def _check_root_user(content: str) -> list[Finding]:
    if _RUN_AS_ROOT.search(content) or _RUN_AS_NON_ROOT_FALSE.search(content):
        evidence = "runAsUser: 0" if _RUN_AS_ROOT.search(content) else "runAsNonRoot: false"
        return [_finding(
            "helm-root-container",
            FindingSeverity.HIGH,
            FindingCategory.SECURITY,
            "Template configures containers to run as root",
            "Setting runAsUser: 0 or runAsNonRoot: false allows the container to run "
            "as the root user, increasing the blast radius of a container escape.",
            "Set runAsNonRoot: true and use an unprivileged UID (e.g. 1000) in values.",
            evidence,
        )]
    return []


def _check_debug_mode(content: str) -> list[Finding]:
    if not _DEBUG_MODE.search(content):
        return []
    return [_finding(
        "helm-debug-mode",
        FindingSeverity.MEDIUM,
        FindingCategory.SECURITY,
        "Debug mode enabled in chart values",
        "A debug flag is set to true. Debug modes commonly enable verbose logging, "
        "profiling endpoints, or relaxed authentication — none of which belong in production.",
        "Set debug to false (or remove it) for production deployments. "
        "Override at install time with --set if needed for local development.",
        "debug: true",
    )]


def _check_default_credentials(content: str) -> list[Finding]:
    if not _DEFAULT_CREDS.search(content):
        return []
    return [_finding(
        "helm-default-credentials",
        FindingSeverity.HIGH,
        FindingCategory.SECURITY,
        "Default administrative credentials in chart values",
        "The chart defaults the username to a well-known admin account name "
        "(admin, root, or administrator). Default credentials are a common attack vector.",
        "Remove the default credential values and require them to be supplied at install "
        "time, or reference an external secret.",
        "username: admin",
    )]


def _check_insecure_registry(content: str) -> list[Finding]:
    if not _INSECURE_REGISTRY.search(content):
        return []
    return [_finding(
        "helm-insecure-registry",
        FindingSeverity.HIGH,
        FindingCategory.SECURITY,
        "Container image pulled from an HTTP (insecure) registry",
        "The chart references an image repository over plain HTTP. Images can be "
        "tampered with in transit (MITM attack).",
        "Use HTTPS registries only. Configure the container runtime to reject insecure "
        "registries at the node level.",
        "repository: http://...",
    )]


def _check_missing_resource_limits(content: str) -> list[Finding]:
    if not _HAS_CONTAINERS.search(content):
        return []
    if _HAS_LIMITS.search(content):
        return []
    return [_finding(
        "helm-missing-resource-limits",
        FindingSeverity.MEDIUM,
        FindingCategory.RELIABILITY,
        "No resource limits defined in chart templates",
        "Container templates have no resources.limits section. Without limits a "
        "single misbehaving container can starve other workloads on the node.",
        "Add resources.limits.cpu and resources.limits.memory to the container spec, "
        "or expose them as chart values so operators can tune them at install time.",
        "resources.limits: <absent>",
    )]


def _check_missing_readiness_probe(content: str) -> list[Finding]:
    if not _HAS_CONTAINERS.search(content):
        return []
    if _HAS_READINESS.search(content):
        return []
    return [_finding(
        "helm-missing-readiness-probe",
        FindingSeverity.MEDIUM,
        FindingCategory.RELIABILITY,
        "No readiness probe defined in chart templates",
        "Without a readinessProbe the Service will route traffic to pods immediately "
        "on startup, before the application is ready to handle requests.",
        "Add a readinessProbe that checks an HTTP health endpoint or executes a "
        "health-check command.",
        "readinessProbe: <absent>",
    )]


# ─── shared helper ────────────────────────────────────────────────────────────

def _finding(
    rule_id: str,
    severity: FindingSeverity,
    category: FindingCategory,
    title: str,
    description: str,
    recommendation: str,
    evidence: str,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        category=category,
        severity=severity,
        title=title,
        description=description,
        recommendation=recommendation,
        line_number=None,
        evidence=evidence,
    )
