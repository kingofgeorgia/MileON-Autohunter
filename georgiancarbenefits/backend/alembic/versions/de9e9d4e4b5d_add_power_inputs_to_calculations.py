"""add power inputs to calculations

Revision ID: de9e9d4e4b5d
Revises: 5437fb538d42
Create Date: 2026-04-08 09:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "de9e9d4e4b5d"
down_revision: Union[str, None] = "5437fb538d42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "calculations",
        sa.Column("horse_power", sa.Numeric(precision=10, scale=2), nullable=True),
    )
    op.add_column(
        "calculations",
        sa.Column("util_coefficient", sa.Numeric(precision=10, scale=4), nullable=True),
    )
    op.add_column(
        "calculations",
        sa.Column(
            "is_personal_use",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("calculations", "is_personal_use")
    op.drop_column("calculations", "util_coefficient")
    op.drop_column("calculations", "horse_power")