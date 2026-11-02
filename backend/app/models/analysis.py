"""Analysis and FindingRecord database models."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FindingChatMessage(Base):
    __tablename__ = "finding_chat_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    finding_id: Mapped[UUID] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    finding: Mapped["FindingRecord"] = relationship("FindingRecord", back_populates="messages")


class FindingRecord(Base):
    __tablename__ = "findings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    analysis_id: Mapped[UUID] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    rule_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    fix_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="findings")
    messages: Mapped[list["FindingChatMessage"]] = relationship(
        "FindingChatMessage", back_populates="finding", cascade="all, delete-orphan"
    )


class Analysis(Base):

    __tablename__ = "analyses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    configuration_id: Mapped[UUID] = mapped_column(
        ForeignKey("configurations.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rule_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    share_token: Mapped[str | None] = mapped_column(
        String(36), nullable=True, unique=True, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    findings: Mapped[list[FindingRecord]] = relationship(
        "FindingRecord", back_populates="analysis", cascade="all, delete-orphan"
    )
