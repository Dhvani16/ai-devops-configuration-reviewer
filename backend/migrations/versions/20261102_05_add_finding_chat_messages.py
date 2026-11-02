"""add finding_chat_messages table

Revision ID: 20261102_05
Revises: 20261102_04
Create Date: 2026-11-02
"""

import sqlalchemy as sa
from alembic import op

revision = "20261102_05"
down_revision = "20261102_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "finding_chat_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("finding_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_finding_chat_messages_finding_id",
        "finding_chat_messages",
        ["finding_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_finding_chat_messages_finding_id", table_name="finding_chat_messages")
    op.drop_table("finding_chat_messages")
