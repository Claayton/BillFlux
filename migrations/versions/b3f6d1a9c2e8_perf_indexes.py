"""perf indexes para vendas/compras/estoque

Revision ID: b3f6d1a9c2e8
Revises: 9a7c3e1f2b4d
Create Date: 2026-10-14 21:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "b3f6d1a9c2e8"
down_revision: Union[str, None] = "9a7c3e1f2b4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEXES = [
    ("ix_orders_created_at", "orders", ["created_at"]),
    ("ix_order_items_order_id", "order_items", ["order_id"]),
    ("ix_order_payments_order_id", "order_payments", ["order_id"]),
    ("ix_productmovement_product_id", "productmovement", ["product_id"]),
    ("ix_purchase_order_created_at", "purchase_order", ["created_at"]),
    ("ix_purchase_item_purchase_id", "purchase_item", ["purchase_id"]),
    ("ix_tab_item_tab_id", "tab_item", ["tab_id"]),
]


def upgrade() -> None:
    for name, table, columns in _INDEXES:
        op.create_index(name, table, columns, unique=False)


def downgrade() -> None:
    for name, table, _columns in reversed(_INDEXES):
        op.drop_index(name, table_name=table)
