"""Rule-based Kubernetes manifest analysis.

Handles single and multi-document YAML (--- separator).
Supports Pod, Deployment, StatefulSet, DaemonSet, Job, and CronJob resources.
"""

import re
from typing import Any

import yaml

from app.analyzers.interface import ConfigurationAnalyzer, InvalidConfigurationError
from app.schemas.finding import ConfigurationType, Finding, FindingCategory, FindingSeverity

_WORKLOAD_KINDS = {"Pod", "Deployment", "StatefulSet", "DaemonSet", "Job", "ReplicaSet"}
_CRONJOB_KIND = "CronJob"
_PINNED_IMAGE = re.compile(r".+@sha256:[0-9a-f]{64}$", re.IGNORECASE)
_TAGGED_IMAGE = re.compile(r".+:[^:]+$")
_LATEST = re.compile(r":(latest)$", re.IGNORECASE)


class KubernetesAnalyzer(ConfigurationAnalyzer):
    configuration_type = ConfigurationType.KUBERNETES

    def analyze(self, content: str) -> list[Finding]:
        documents = _load_documents(content)
        findings: list[Finding] = []
        for doc in documents:
            if not isinstance(doc, dict):
                continue
            kind = str(doc.get("kind", ""))
            if kind in _WORKLOAD_KINDS:
                pod_spec = _extract_pod_spec(doc, kind)
                if pod_spec:
                    findings.extend(_analyze_pod_spec(pod_spec, kind, doc))
            elif kind == _CRONJOB_KIND:
                pod_spec = _extract_cronjob_pod_spec(doc)
                if pod_spec:
                    findings.extend(_analyze_pod_spec(pod_spec, kind, doc))
        return findings


# ─── helpers ─────────────────────────────────────────────────────────────────

def _load_documents(content: str) -> list[Any]:
    try:
        return list(yaml.safe_load_all(content))
    except yaml.YAMLError as error:
        raise InvalidConfigurationError("Kubernetes YAML is invalid") from error


def _extract_pod_spec(doc: dict[str, Any], kind: str) -> dict[str, Any] | None:
    if kind == "Pod":
        return doc.get("spec") if isinstance(doc.get("spec"), dict) else None
    return (
        doc.get("spec", {})
           .get("template", {})
           .get("spec")
    )


def _extract_cronjob_pod_spec(doc: dict[str, Any]) -> dict[str, Any] | None:
    return (
        doc.get("spec", {})
           .get("jobTemplate", {})
           .get("spec", {})
           .get("template", {})
           .get("spec")
    )


def _analyze_pod_spec(
    pod_spec: dict[str, Any], kind: str, doc: dict[str, Any]
) -> list[Finding]:
    findings: list[Finding] = []
    name = doc.get("metadata", {}).get("name", kind)
    namespace = doc.get("metadata", {}).get("namespace", "default")

    if namespace == "default":
        findings.append(_finding(
            "k8s-default-namespace",
            FindingSeverity.LOW,
            FindingCategory.MAINTAINABILITY,
            "Resource deployed to the default namespace",
            f"{kind} '{name}' uses the default namespace, which makes it harder to apply "
            "network policies and RBAC boundaries.",
            "Deploy workloads to a dedicated namespace and apply appropriate RBAC and network policies.",
            f"namespace: {namespace}",
        ))

    if pod_spec.get("hostNetwork") is True:
        findings.append(_finding(
            "k8s-host-network",
            FindingSeverity.HIGH,
            FindingCategory.SECURITY,
            "Pod uses host network",
            f"{kind} '{name}' sets hostNetwork: true, removing network isolation between "
            "the pod and the host.",
            "Remove hostNetwork unless strictly required; use a Service instead.",
            "hostNetwork: true",
        ))

    if pod_spec.get("hostPID") is True:
        findings.append(_finding(
            "k8s-host-pid",
            FindingSeverity.HIGH,
            FindingCategory.SECURITY,
            "Pod shares host PID namespace",
            f"{kind} '{name}' sets hostPID: true, allowing the container to see and signal "
            "host processes.",
            "Remove hostPID unless strictly required by a debugging or monitoring tool.",
            "hostPID: true",
        ))

    for container in _containers(pod_spec):
        findings.extend(_analyze_container(container, kind, name))

    return findings


def _analyze_container(
    container: dict[str, Any], kind: str, workload_name: str
) -> list[Finding]:
    findings: list[Finding] = []
    cname = container.get("name", "unnamed")
    label = f"{kind}/{workload_name} container '{cname}'"

    image = str(container.get("image", ""))
    if image:
        if _PINNED_IMAGE.match(image):
            pass  # digest-pinned — fine
        elif not _TAGGED_IMAGE.match(image) or _LATEST.search(image):
            findings.append(_finding(
                "k8s-unpinned-image",
                FindingSeverity.MEDIUM,
                FindingCategory.RELIABILITY,
                "Container image is not pinned",
                f"{label} uses image '{image}' which can change between deployments.",
                "Pin the image to a specific version tag or immutable digest (@sha256:...).",
                f"image: {image}",
            ))

    sec = container.get("securityContext", {}) or {}
    if sec.get("privileged") is True:
        findings.append(_finding(
            "k8s-privileged-container",
            FindingSeverity.CRITICAL,
            FindingCategory.SECURITY,
            "Container runs in privileged mode",
            f"{label} sets privileged: true, granting near-host-level access.",
            "Remove privileged mode; add only the specific capabilities required.",
            "privileged: true",
        ))

    run_as_non_root = sec.get("runAsNonRoot")
    run_as_user = sec.get("runAsUser")
    if run_as_non_root is False or run_as_user == 0:
        findings.append(_finding(
            "k8s-root-container",
            FindingSeverity.HIGH,
            FindingCategory.SECURITY,
            "Container is configured to run as root",
            f"{label} explicitly runs as the root user.",
            "Set runAsNonRoot: true and choose an unprivileged runAsUser (e.g. 1000).",
            f"runAsUser: {run_as_user or 0}",
        ))
    elif run_as_non_root is None and run_as_user is None:
        findings.append(_finding(
            "k8s-no-run-as-non-root",
            FindingSeverity.MEDIUM,
            FindingCategory.SECURITY,
            "Container does not explicitly prevent running as root",
            f"{label} has no runAsNonRoot or runAsUser set; the container may run as root "
            "depending on the image.",
            "Set securityContext.runAsNonRoot: true to prevent accidental root execution.",
            f"container: {cname}",
        ))

    resources = container.get("resources", {}) or {}
    limits = resources.get("limits", {}) or {}
    if not limits.get("cpu") or not limits.get("memory"):
        findings.append(_finding(
            "k8s-missing-resource-limits",
            FindingSeverity.MEDIUM,
            FindingCategory.RELIABILITY,
            "Container has no CPU or memory limits",
            f"{label} does not define resource limits, risking noisy-neighbour issues "
            "and potential node OOM kills.",
            "Set resources.limits.cpu and resources.limits.memory to appropriate values.",
            f"container: {cname}",
        ))

    if not container.get("readinessProbe"):
        findings.append(_finding(
            "k8s-missing-readiness-probe",
            FindingSeverity.MEDIUM,
            FindingCategory.RELIABILITY,
            "Container has no readiness probe",
            f"{label} has no readinessProbe; the Service may route traffic to the container "
            "before it is ready to handle requests.",
            "Add a readinessProbe that checks the application's health endpoint or process.",
            f"container: {cname}",
        ))

    return findings


def _containers(pod_spec: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for key in ("containers", "initContainers"):
        items = pod_spec.get(key, [])
        if isinstance(items, list):
            result.extend(c for c in items if isinstance(c, dict))
    return result


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
