"""add scheduled_order

Revision ID: 8f1a2b3c4d5e
Revises: bbb85e66961d
Create Date: 2026-10-11 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "8f1a2b3c4d5e"
down_revision: Union[str, None] = "bbb85e66961d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scheduled_order",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("customer_name", sa.String(), nullable=True),
        sa.Column("order_date", sa.Date(), nullable=True),
        sa.Column("order_time", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("obs", sa.String(), nullable=True),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column("items", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customer.id"]),
    )
    op.create_index("ix_scheduled_order_order_date", "scheduled_order", ["order_date"])
    op.create_index("ix_scheduled_order_status", "scheduled_order", ["status"])
    op.create_index(
        "ix_scheduled_order_customer_id", "scheduled_order", ["customer_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_scheduled_order_customer_id", table_name="scheduled_order")
    op.drop_index("ix_scheduled_order_status", table_name="scheduled_order")
    op.drop_index("ix_scheduled_order_order_date", table_name="scheduled_order")
    op.drop_table("scheduled_order")
