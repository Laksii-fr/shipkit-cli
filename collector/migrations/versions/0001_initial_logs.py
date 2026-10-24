"""Initial logs table.

Revision ID: 0001
Revises:
Create Date: 2026-10-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service", sa.String(length=200), nullable=False),
        sa.Column("ts", sa.DateTime(), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
    )
    op.create_index("ix_logs_service_ts", "logs", ["service", "ts"])
    op.create_index("ix_logs_level", "logs", ["level"])


def downgrade() -> None:
    op.drop_index("ix_logs_level", table_name="logs")
    op.drop_index("ix_logs_service_ts", table_name="logs")
    op.drop_table("logs")
