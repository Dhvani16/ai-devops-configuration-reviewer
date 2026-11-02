"""add share_token to analyses

Revision ID: 20261102_06
Revises: 20261102_05
Create Date: 2026-11-02
"""

import sqlalchemy as sa
from alembic import op

revision = "20261102_06"
down_revision = "20261102_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("share_token", sa.String(36), nullable=True))
    op.create_index("ix_analyses_share_token", "analyses", ["share_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_analyses_share_token", table_name="analyses")
    op.drop_column("analyses", "share_token")
