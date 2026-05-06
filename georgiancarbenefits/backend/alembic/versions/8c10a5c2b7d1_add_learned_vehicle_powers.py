"""add learned vehicle powers

Revision ID: 8c10a5c2b7d1
Revises: 2c6d4d8e9f01
Create Date: 2026-04-08 18:35:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8c10a5c2b7d1"
down_revision: Union[str, None] = "2c6d4d8e9f01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learned_vehicle_powers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("make", sa.String(length=120), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("normalized_make", sa.String(length=120), nullable=False),
        sa.Column("normalized_model", sa.String(length=160), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=True),
        sa.Column("horse_power", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_learned_vehicle_powers_id"), "learned_vehicle_powers", ["id"], unique=False)
    op.create_index(op.f("ix_learned_vehicle_powers_model_id"), "learned_vehicle_powers", ["model_id"], unique=False)
    op.create_index(op.f("ix_learned_vehicle_powers_normalized_make"), "learned_vehicle_powers", ["normalized_make"], unique=False)
    op.create_index(op.f("ix_learned_vehicle_powers_normalized_model"), "learned_vehicle_powers", ["normalized_model"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_learned_vehicle_powers_normalized_model"), table_name="learned_vehicle_powers")
    op.drop_index(op.f("ix_learned_vehicle_powers_normalized_make"), table_name="learned_vehicle_powers")
    op.drop_index(op.f("ix_learned_vehicle_powers_model_id"), table_name="learned_vehicle_powers")
    op.drop_index(op.f("ix_learned_vehicle_powers_id"), table_name="learned_vehicle_powers")
    op.drop_table("learned_vehicle_powers")