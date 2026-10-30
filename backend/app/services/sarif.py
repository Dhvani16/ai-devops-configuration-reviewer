"""SARIF 2.1 serialiser for analysis findings.

Produces a minimal but valid SARIF document compatible with GitHub Code Scanning
(sarif-schema-2.1.0).  Only fields that GitHub actually requires / displays are
populated; optional fields are omitted to keep the output lean.
"""

from __future__ import annotations

from typing import Any

from app.models.analysis import Analysis, FindingRecord

_SARIF_VERSION = "2.1.0"
_SARIF_SCHEMA = "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json"

_SEVERITY_MAP = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
}


def analysis_to_sarif(analysis: Analysis) -> dict[str, Any]:
    """Return a SARIF 2.1 document as a plain dict (ready for JSON serialisation)."""
    rules = _build_rules(analysis.findings)
    results = [_finding_to_result(f) for f in analysis.findings]
    return {
        "$schema": _SARIF_SCHEMA,
        "version": _SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "AI DevOps Reviewer",
                        "version": "1.0.0",
                        "informationUri": "https://github.com/dhvani/ai-devops-configuration-reviewer",
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
                "automationDetails": {
                    "id": str(analysis.id),
                },
            }
        ],
    }


# ─── private helpers ──────────────────────────────────────────────────────────

def _build_rules(findings: list[FindingRecord]) -> dict[str, dict[str, Any]]:
    rules: dict[str, dict[str, Any]] = {}
    for f in findings:
        rule_id = f.rule_id or f"finding-{f.id}"
        if rule_id in rules:
            continue
        rules[rule_id] = {
            "id": rule_id,
            "name": _to_pascal_case(f.title),
            "shortDescription": {"text": f.title},
            "fullDescription": {"text": f.description},
            "helpUri": "",
            "properties": {
                "tags": [f.category],
                "precision": "high" if f.source == "deterministic" else "medium",
                "problem.severity": _SEVERITY_MAP.get(f.severity, "warning"),
            },
        }
    return rules


def _finding_to_result(f: FindingRecord) -> dict[str, Any]:
    rule_id = f.rule_id or f"finding-{f.id}"
    result: dict[str, Any] = {
        "ruleId": rule_id,
        "level": _SEVERITY_MAP.get(f.severity, "warning"),
        "message": {"text": f.description},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": "configuration", "uriBaseId": "%SRCROOT%"},
                    **(
                        {"region": {"startLine": f.line_number}}
                        if f.line_number
                        else {}
                    ),
                }
            }
        ],
    }
    if f.confidence is not None:
        result["properties"] = {"confidence": round(f.confidence, 3)}
    return result


def _to_pascal_case(title: str) -> str:
    return "".join(word.capitalize() for word in title.split()[:6])
