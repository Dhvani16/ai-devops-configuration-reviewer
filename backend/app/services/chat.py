"""Remediation chat service — per-finding AI conversation."""

import logging
from uuid import UUID

from openai import AsyncOpenAI, APIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.analysis import Analysis, FindingChatMessage, FindingRecord
from app.models.configuration import Configuration

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a DevOps security expert helping a developer understand a specific security "
    "finding in their configuration file. Answer questions concisely and practically. "
    "When asked for code examples or fixes, provide short, focused snippets only. "
    "Keep answers under 300 words unless more detail is genuinely needed."
)


async def get_finding_for_user(
    session: AsyncSession, finding_id: UUID, user_id: UUID
) -> FindingRecord | None:
    result = await session.execute(
        select(FindingRecord)
        .join(Analysis, FindingRecord.analysis_id == Analysis.id)
        .join(Configuration, Analysis.configuration_id == Configuration.id)
        .where(FindingRecord.id == finding_id, Configuration.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_chat_history(
    session: AsyncSession, finding_id: UUID
) -> list[FindingChatMessage]:
    result = await session.execute(
        select(FindingChatMessage)
        .where(FindingChatMessage.finding_id == finding_id)
        .order_by(FindingChatMessage.created_at)
    )
    return list(result.scalars().all())


async def send_chat_message(
    session: AsyncSession,
    finding: FindingRecord,
    user_message: str,
    settings: Settings,
) -> FindingChatMessage:
    context = (
        f"Title: {finding.title}\n"
        f"Severity: {finding.severity}\n"
        f"Category: {finding.category}\n"
        f"Description: {finding.description}\n"
        f"Recommendation: {finding.recommendation}\n"
        f"Evidence:\n{finding.evidence}"
    )
    if finding.fix_suggestion:
        context += f"\nSuggested fix already provided:\n{finding.fix_suggestion}"

    system_prompt = f"{_SYSTEM}\n\nFinding context:\n{context}"

    history = await get_chat_history(session, finding.id)
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=500,
        )
        assistant_text = response.choices[0].message.content or ""
    except APIError as exc:
        logger.warning("Chat AI call failed: %s", exc)
        assistant_text = "Sorry, I couldn't reach the AI service right now. Please try again."

    user_record = FindingChatMessage(
        finding_id=finding.id, role="user", content=user_message
    )
    asst_record = FindingChatMessage(
        finding_id=finding.id, role="assistant", content=assistant_text
    )
    session.add(user_record)
    session.add(asst_record)
    await session.commit()
    await session.refresh(asst_record)
    return asst_record
