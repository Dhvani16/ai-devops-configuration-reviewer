"""Prompt construction for configuration analysis."""

import json

from app.ai.schemas import AIAnalysisRequest

SYSTEM_PROMPT = """You are a careful DevOps configuration reviewer. Analyze only the supplied configuration.
Use the deterministic findings as context, but avoid duplicating them unless important context is missing.
Do not invent vulnerabilities or make unsupported claims. Explain impact and give actionable remediation.
Reference relevant line numbers when possible. The response must conform to the supplied JSON schema."""


def build_analysis_input(request: AIAnalysisRequest) -> str:
    """Build compact dynamic context after the stable system prompt."""
    deterministic_findings = [
        finding.model_dump(mode="json") for finding in request.deterministic_findings
    ]
    return (
        f"Configuration type: {request.configuration_type.value}\n\n"
        "Deterministic findings:\n"
        f"{json.dumps(deterministic_findings, separators=(',', ':'))}\n\n"
        "Configuration:\n"
        f"{request.content}"
    )
