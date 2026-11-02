"""Add fix_suggestion column to findings table.

Revision ID: 20261102_03
Revises: 20260824_02
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261102_03"
down_revision: str | None = "20260824_02"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("findings", sa.Column("fix_suggestion", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("findings", "fix_suggestion")
