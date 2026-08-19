"""Module for model OrderItem (itens dos pedidos do PDV)"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import SQLModel, Field


class OrderItem(SQLModel, table=True):
    """Itens de um pedido do PDV"""

    __tablename__ = "order_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: Optional[int] = Field(
        default=None, foreign_key="orders.id", nullable=False
    )
    product_id: Optional[int] = Field(
        default=None, foreign_key="product.id", nullable=False
    )
    quantity: int = Field(nullable=False)
    unit_price: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
