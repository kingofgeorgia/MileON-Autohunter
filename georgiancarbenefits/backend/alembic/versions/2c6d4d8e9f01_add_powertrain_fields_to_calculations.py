"""add powertrain fields to calculations

Revision ID: 2c6d4d8e9f01
Revises: de9e9d4e4b5d
Create Date: 2026-04-08 12:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2c6d4d8e9f01"
down_revision: Union[str, None] = "de9e9d4e4b5d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "calculations",
        sa.Column("powertrain_kind", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "calculations",
        sa.Column("power_kw_override", sa.Numeric(precision=10, scale=2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("calculations", "power_kw_override")
    op.drop_column("calculations", "powertrain_kind")