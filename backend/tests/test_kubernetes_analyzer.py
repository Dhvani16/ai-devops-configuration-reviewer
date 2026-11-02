"""Tests for the Kubernetes manifest analyzer."""

import pytest

from app.analyzers.interface import InvalidConfigurationError
from app.analyzers.kubernetes import KubernetesAnalyzer

_BASE_DEPLOYMENT = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: production
spec:
  template:
    spec:
      containers:
        - name: api
          image: myapp:1.2.3
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
          resources:
            limits:
              cpu: "500m"
              memory: "256Mi"
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
"""


@pytest.mark.parametrize(
    ("old_str", "new_str", "rule_id"),
    [
        # default namespace
        ("namespace: production", "namespace: default", "k8s-default-namespace"),
        # hostNetwork — injected into pod spec (spec.template.spec)
        ("      containers:", "      hostNetwork: true\n      containers:", "k8s-host-network"),
        # hostPID — injected into pod spec
        ("      containers:", "      hostPID: true\n      containers:", "k8s-host-pid"),
        # unpinned image (latest)
        ("image: myapp:1.2.3", "image: myapp:latest", "k8s-unpinned-image"),
        # unpinned image (no tag)
        ("image: myapp:1.2.3", "image: myapp", "k8s-unpinned-image"),
        # privileged
        ("runAsNonRoot: true", "privileged: true", "k8s-privileged-container"),
        # root user
        ("runAsUser: 1000", "runAsUser: 0", "k8s-root-container"),
        # missing resource limits
        (
            "resources:\n            limits:\n              cpu: \"500m\"\n              memory: \"256Mi\"",
            "resources: {}",
            "k8s-missing-resource-limits",
        ),
        # missing readiness probe
        (
            "readinessProbe:\n            httpGet:\n              path: /health\n              port: 8080",
            "",
            "k8s-missing-readiness-probe",
        ),
    ],
)
def test_kubernetes_rules(old_str: str, new_str: str, rule_id: str) -> None:
    content = _BASE_DEPLOYMENT.replace(old_str, new_str, 1)
    findings = KubernetesAnalyzer().analyze(content)
    assert rule_id in {f.rule_id for f in findings}, (
        f"Expected rule {rule_id!r} not found in: {[f.rule_id for f in findings]}"
    )


def test_clean_deployment_has_no_findings() -> None:
    findings = KubernetesAnalyzer().analyze(_BASE_DEPLOYMENT)
    assert findings == []


def test_multi_document_manifest() -> None:
    multi = _BASE_DEPLOYMENT + "\n---\n" + _BASE_DEPLOYMENT.replace(
        "image: myapp:1.2.3", "image: myapp:latest"
    )
    rule_ids = {f.rule_id for f in KubernetesAnalyzer().analyze(multi)}
    assert "k8s-unpinned-image" in rule_ids


def test_digest_pinned_image_is_not_flagged() -> None:
    content = _BASE_DEPLOYMENT.replace(
        "image: myapp:1.2.3",
        "image: myapp@sha256:" + "a" * 64,
    )
    rule_ids = {f.rule_id for f in KubernetesAnalyzer().analyze(content)}
    assert "k8s-unpinned-image" not in rule_ids


def test_pod_kind_is_analyzed() -> None:
    pod = """
apiVersion: v1
kind: Pod
metadata:
  name: test
  namespace: default
spec:
  containers:
    - name: app
      image: nginx
"""
    rule_ids = {f.rule_id for f in KubernetesAnalyzer().analyze(pod)}
    assert "k8s-default-namespace" in rule_ids
    assert "k8s-unpinned-image" in rule_ids


def test_invalid_yaml_raises() -> None:
    with pytest.raises(InvalidConfigurationError):
        KubernetesAnalyzer().analyze("this: is: not: valid: yaml: [[[")


def test_factory_includes_kubernetes() -> None:
    from app.analyzers.factory import get_analyzer
    from app.schemas.finding import ConfigurationType

    analyzer = get_analyzer(ConfigurationType.KUBERNETES)
    assert isinstance(analyzer, KubernetesAnalyzer)
