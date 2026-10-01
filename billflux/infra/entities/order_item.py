"""Module for model OrderItem (itens dos pedidos do PDV)"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import SQLModel, Field


class OrderItem(SQLModel, table=True):
    """Itens de um pedido do PDV

    `quantity`/`unit_price` são da apresentação vendida (ex.: 1 caixa a
    R$ 45,99). `factor` é quantas unidades-base a apresentação representa
    (ex.: 15), usado pra baixar estoque e calcular lucro."""

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
    factor: int = Field(nullable=False, default=1)
