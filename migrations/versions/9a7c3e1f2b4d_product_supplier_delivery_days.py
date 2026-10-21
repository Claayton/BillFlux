"""add productsupplier.delivery_days (múltiplos dias por semana)

Revision ID: 9a7c3e1f2b4d
Revises: bbb85e66961d
Create Date: 2026-10-14 20:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "9a7c3e1f2b4d"
down_revision: Union[str, None] = "bbb85e66961d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("productsupplier", schema=None) as batch_op:
        batch_op.add_column(sa.Column("delivery_days", sa.Text(), nullable=True))

    # Retrocompatibilidade: cada vínculo antigo vira uma lista de 1 dia.
    op.execute(
        "UPDATE productsupplier "
        "SET delivery_days = '[' || delivery_day || ']' "
        "WHERE delivery_days IS NULL"
    )


def downgrade() -> None:
    with op.batch_alter_table("productsupplier", schema=None) as batch_op:
        batch_op.drop_column("delivery_days")
