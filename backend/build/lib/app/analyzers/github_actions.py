"""Rule-based GitHub Actions workflow analysis."""

import re
from typing import Any

import yaml

from app.analyzers.interface import ConfigurationAnalyzer, InvalidConfigurationError
from app.analyzers.utils import find_line_number
from app.schemas.finding import ConfigurationType, Finding, FindingCategory, FindingSeverity

FULL_SHA = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
DANGEROUS_EXPRESSION = re.compile(r"\$\{\{\s*(github\.event|inputs\.)", re.IGNORECASE)


class GitHubActionsAnalyzer(ConfigurationAnalyzer):
    configuration_type = ConfigurationType.GITHUB_ACTIONS

    def analyze(self, content: str) -> list[Finding]:
        workflow = _load_workflow(content)
        findings: list[Finding] = []
        if "pull_request_target" in _triggers(workflow):
            findings.append(
                _finding(
                    "actions-pull-request-target",
                    FindingSeverity.HIGH,
                    "pull_request_target",
                    content,
                )
            )
        findings.extend(_permission_findings(workflow.get("permissions"), content))

        jobs = workflow.get("jobs")
        if not isinstance(jobs, dict):
            raise InvalidConfigurationError("GitHub Actions workflow must contain a jobs mapping")
        for job in jobs.values():
            if not isinstance(job, dict):
                continue
            findings.extend(_permission_findings(job.get("permissions"), content))
            for step in job.get("steps", []):
                if not isinstance(step, dict):
                    continue
                uses = step.get("uses")
                if (
                    isinstance(uses, str)
                    and not uses.startswith(("./", "docker://"))
                    and not _is_pinned(uses)
                ):
                    findings.append(
                        _finding("actions-unpinned-action", FindingSeverity.MEDIUM, uses, content)
                    )
                run = step.get("run")
                if isinstance(run, str) and DANGEROUS_EXPRESSION.search(run):
                    findings.append(
                        _finding(
                            "actions-untrusted-shell-input", FindingSeverity.HIGH, run, content
                        )
                    )
                if isinstance(run, str) and re.search(r"echo.+secrets\.", run, re.IGNORECASE):
                    findings.append(
                        _finding("actions-secret-in-logs", FindingSeverity.CRITICAL, run, content)
                    )
        return findings


def _load_workflow(content: str) -> dict[str, Any]:
    try:
        workflow = yaml.safe_load(content)
    except yaml.YAMLError as error:
        raise InvalidConfigurationError("GitHub Actions YAML is invalid") from error
    if not isinstance(workflow, dict):
        raise InvalidConfigurationError("GitHub Actions workflow must be a YAML mapping")
    return workflow


def _triggers(workflow: dict[str, Any]) -> list[str]:
    value = workflow.get("on", workflow.get(True, []))
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, dict):
        return [str(item) for item in value]
    return []


def _permission_findings(permissions: Any, content: str) -> list[Finding]:
    if permissions == "write-all":
        return [
            _finding(
                "actions-write-all-permissions",
                FindingSeverity.HIGH,
                "permissions: write-all",
                content,
            )
        ]
    if isinstance(permissions, dict):
        return [
            _finding("actions-write-permission", FindingSeverity.HIGH, f"{scope}: write", content)
            for scope, access in permissions.items()
            if str(access).lower() == "write"
        ]
    return []


def _is_pinned(uses: str) -> bool:
    return "@" in uses and bool(FULL_SHA.fullmatch(uses.rsplit("@", 1)[1]))


def _finding(rule_id: str, severity: FindingSeverity, evidence: str, content: str) -> Finding:
    descriptions = {
        "actions-pull-request-target": "This trigger can run with elevated repository permissions for pull requests.",
        "actions-unpinned-action": "A mutable action reference can change without a workflow change.",
        "actions-write-all-permissions": "write-all grants a broad write-capable GITHUB_TOKEN.",
        "actions-write-permission": "A write-capable token permission should be limited to the minimum required scope.",
        "actions-untrusted-shell-input": "User-controlled workflow data may be interpreted by the shell.",
        "actions-secret-in-logs": "Writing a secret expression to output risks exposing it in workflow logs.",
    }
    recommendations = {
        "actions-pull-request-target": "Use pull_request where possible and avoid checking out untrusted pull request code.",
        "actions-unpinned-action": "Pin third-party actions to a full commit SHA and document the version separately.",
        "actions-write-all-permissions": "Declare only the minimum required permissions at workflow or job level.",
        "actions-write-permission": "Remove unnecessary write access and scope required write permissions narrowly.",
        "actions-untrusted-shell-input": "Pass untrusted values through environment variables and quote them in shell commands.",
        "actions-secret-in-logs": "Do not echo secrets; pass them directly to the consuming command.",
    }
    titles = {
        "actions-pull-request-target": "Risky pull_request_target trigger",
        "actions-unpinned-action": "Action is not pinned to a commit SHA",
        "actions-write-all-permissions": "Workflow grants write-all permissions",
        "actions-write-permission": "Workflow grants write permission",
        "actions-untrusted-shell-input": "Untrusted input used in shell command",
        "actions-secret-in-logs": "Secret may be written to workflow logs",
    }
    return Finding(
        rule_id=rule_id,
        category=FindingCategory.SECURITY,
        severity=severity,
        title=titles[rule_id],
        description=descriptions[rule_id],
        recommendation=recommendations[rule_id],
        line_number=find_line_number(content, re.escape(evidence)),
        evidence=evidence,
    )
