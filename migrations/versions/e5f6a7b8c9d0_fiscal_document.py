"""tabela fiscal_document (NFC-e do PDV)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-10 15:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fiscal_document",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.Integer(), nullable=False),
        sa.Column("environment", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("series", sa.Integer(), nullable=True),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("access_key", sa.String(length=44), nullable=True),
        sa.Column("protocol", sa.String(length=60), nullable=True),
        sa.Column("xml", sa.Text(), nullable=True),
        sa.Column("danfe", sa.Text(), nullable=True),
        sa.Column("qr_code_url", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=20), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("authorized_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
    )
    op.create_index(
        "ix_fiscal_document_order_id",
        "fiscal_document",
        ["order_id"],
        unique=True,
    )
    op.create_index(
        "ix_fiscal_document_status", "fiscal_document", ["status"], unique=False
    )
    op.create_index(
        "ix_fiscal_document_access_key",
        "fiscal_document",
        ["access_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_fiscal_document_access_key", table_name="fiscal_document")
    op.drop_index("ix_fiscal_document_status", table_name="fiscal_document")
    op.drop_index("ix_fiscal_document_order_id", table_name="fiscal_document")
    op.drop_table("fiscal_document")
