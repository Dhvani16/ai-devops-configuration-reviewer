"""Add rule_version column to analyses table.

Revision ID: 20261102_04
Revises: 20261102_03
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261102_04"
down_revision: str | None = "20261102_03"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("rule_version", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "rule_version")
