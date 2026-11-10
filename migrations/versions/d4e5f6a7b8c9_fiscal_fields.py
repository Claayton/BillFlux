"""campos fiscais de produto e dados da NF-e de compra

Revision ID: d4e5f6a7b8c9
Revises: b3f6d1a9c2e8
Create Date: 2026-11-10 10:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "b3f6d1a9c2e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("product", schema=None) as batch_op:
        batch_op.add_column(sa.Column("ncm", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("cest", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("cfop", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("csosn", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("cst", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("origem", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("fiscal_unit", sa.Text(), nullable=True))
        batch_op.create_index("ix_product_ncm", ["ncm"], unique=False)

    with op.batch_alter_table("purchase_item", schema=None) as batch_op:
        batch_op.add_column(sa.Column("ncm", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("cfop", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("purchase_item", schema=None) as batch_op:
        batch_op.drop_column("cfop")
        batch_op.drop_column("ncm")

    with op.batch_alter_table("product", schema=None) as batch_op:
        batch_op.drop_index("ix_product_ncm")
        batch_op.drop_column("fiscal_unit")
        batch_op.drop_column("origem")
        batch_op.drop_column("cst")
        batch_op.drop_column("csosn")
        batch_op.drop_column("cfop")
        batch_op.drop_column("cest")
        batch_op.drop_column("ncm")
