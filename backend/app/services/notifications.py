"""Slack webhook notification for completed analyses.

Silently skips if SLACK_WEBHOOK_URL is not configured.
Uses httpx (already a transitive dep via fastapi) for the HTTP call.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def notify_analysis_complete(
    analysis_id: str,
    configuration_name: str,
    configuration_type: str,
    overall_score: float,
    finding_count: int,
    webhook_url: str | None,
) -> None:
    if not webhook_url:
        return

    score_emoji = _score_emoji(overall_score)
    text = (
        f"{score_emoji} *AI DevOps Reviewer* analysis complete\n"
        f"*Configuration:* {configuration_name} (`{configuration_type}`)\n"
        f"*Score:* {overall_score:.0f}/100  |  *Findings:* {finding_count}\n"
        f"*Analysis ID:* `{analysis_id}`"
    )

    try:
        import httpx

        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(webhook_url, json={"text": text})
            if response.status_code != 200:
                logger.warning(
                    "Slack webhook returned %s: %s", response.status_code, response.text
                )
    except Exception as exc:
        logger.warning("Failed to send Slack notification: %s", exc)


def _score_emoji(score: float) -> str:
    if score >= 80:
        return ":white_check_mark:"
    if score >= 60:
        return ":large_yellow_circle:"
    if score >= 40:
        return ":warning:"
    return ":red_circle:"
