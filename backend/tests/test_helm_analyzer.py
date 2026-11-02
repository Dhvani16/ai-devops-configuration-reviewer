"""Tests for HelmAnalyzer."""

import pytest

from app.analyzers.helm import HelmAnalyzer
from app.analyzers.interface import InvalidConfigurationError

_CLEAN_VALUES = """\
replicaCount: 1

image:
  repository: myregistry.example.com/myapp
  pullPolicy: IfNotPresent
  tag: "1.2.3"

service:
  type: ClusterIP
  port: 80

resources:
  limits:
    cpu: 200m
    memory: 256Mi
  requests:
    cpu: 100m
    memory: 128Mi

securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  privileged: false

debug: false
"""

_CLEAN_TEMPLATE = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "myapp.fullname" . }}
spec:
  template:
    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          resources:
            limits:
              cpu: {{ .Values.resources.limits.cpu }}
              memory: {{ .Values.resources.limits.memory }}
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
"""

analyzer = HelmAnalyzer()


def _rule_ids(content: str) -> set[str]:
    return {f.rule_id for f in analyzer.analyze(content)}


# ─── validation ───────────────────────────────────────────────────────────────

def test_empty_content_raises():
    with pytest.raises(InvalidConfigurationError):
        analyzer.analyze("")


def test_non_helm_content_raises():
    with pytest.raises(InvalidConfigurationError):
        analyzer.analyze("just some plain text without any yaml markers")


# ─── clean fixtures produce no findings ───────────────────────────────────────

def test_clean_values_no_findings():
    assert _rule_ids(_CLEAN_VALUES) == set()


def test_clean_template_no_findings():
    assert _rule_ids(_CLEAN_TEMPLATE) == set()


# ─── individual rules ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("snippet,expected_rule", [
    ('password: "supersecret123"', "helm-hardcoded-secret"),
    ('secretKey: "abc123xyz"', "helm-hardcoded-secret"),
    ("privileged: true", "helm-privileged-container"),
    ("hostNetwork: true", "helm-host-network"),
    ("runAsUser: 0", "helm-root-container"),
    ("runAsNonRoot: false", "helm-root-container"),
    ("debug: true", "helm-debug-mode"),
    ("username: admin", "helm-default-credentials"),
    ("repository: http://my-registry/myapp", "helm-insecure-registry"),
])
def test_rule_fires(snippet: str, expected_rule: str):
    content = _CLEAN_VALUES + "\n" + snippet
    assert expected_rule in _rule_ids(content), (
        f"Expected rule '{expected_rule}' not found in: {_rule_ids(content)}"
    )


def test_missing_resource_limits_fires():
    content = """\
image:
  repository: myregistry/myapp
containers:
  - name: myapp
    image: myapp:1.0
"""
    assert "helm-missing-resource-limits" in _rule_ids(content)


def test_missing_readiness_probe_fires():
    content = """\
image:
  repository: myregistry/myapp
containers:
  - name: myapp
    image: myapp:1.0
    resources:
      limits:
        cpu: 100m
        memory: 128Mi
"""
    assert "helm-missing-readiness-probe" in _rule_ids(content)


def test_template_value_not_flagged_as_secret():
    content = _CLEAN_VALUES + '\npassword: "{{ .Values.auth.password }}"'
    assert "helm-hardcoded-secret" not in _rule_ids(content)


def test_placeholder_value_not_flagged():
    content = _CLEAN_VALUES + '\npassword: "changeme"'
    assert "helm-hardcoded-secret" not in _rule_ids(content)


def test_resource_limits_present_no_finding():
    assert "helm-missing-resource-limits" not in _rule_ids(_CLEAN_VALUES)


def test_readiness_probe_present_no_finding():
    assert "helm-missing-readiness-probe" not in _rule_ids(_CLEAN_TEMPLATE)
