"""AI-powered score explanation service."""

import logging

from openai import APIError, AsyncOpenAI

from app.core.config import Settings
from app.models.analysis import Analysis

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a DevOps security expert explaining a configuration analysis risk score to a developer. "
    "Be direct, practical, and prioritise actionability. Use plain language, no bullet points."
)


def _build_prompt(analysis: Analysis) -> str:
    findings = analysis.findings
    severity_counts = {s: 0 for s in ("critical", "high", "medium", "low")}
    for f in findings:
        if f.severity in severity_counts:
            severity_counts[f.severity] += 1

    ai_count = sum(1 for f in findings if f.source == "ai")
    static_count = len(findings) - ai_count

    top = sorted(
        findings,
        key=lambda f: ["critical", "high", "medium", "low"].index(f.severity)
        if f.severity in ["critical", "high", "medium", "low"]
        else 99,
    )[:5]

    top_lines = "\n".join(f"- [{f.severity.upper()}] {f.title}" for f in top) or "None"

    score = round(analysis.overall_score or 0)
    return (
        f"Risk score: {score}/100 (0 = maximum risk, 100 = clean)\n"
        f"Findings: {severity_counts['critical']} critical, {severity_counts['high']} high, "
        f"{severity_counts['medium']} medium, {severity_counts['low']} low "
        f"({static_count} static, {ai_count} AI-detected)\n\n"
        f"Most severe findings:\n{top_lines}\n\n"
        "In 3-5 sentences: explain why the configuration received this score, "
        "highlight the most important issues, and state what to fix first."
    )


async def explain_score(analysis: Analysis, settings: Settings) -> str:
    prompt = _build_prompt(analysis)
    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content or ""
    except APIError as exc:
        logger.warning("explain_score AI call failed: %s", exc)
        return "Unable to generate explanation — AI service unavailable."
