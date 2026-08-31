"""Module for model PurchaseItem (itens de compra)"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import SQLModel, Field


class PurchaseItem(SQLModel, table=True):
    """Itens de uma compra"""

    __tablename__ = "purchase_item"

    id: Optional[int] = Field(default=None, primary_key=True)
    purchase_id: Optional[int] = Field(
        default=None, foreign_key="purchase_order.id", nullable=False
    )
    product_id: Optional[int] = Field(
        default=None, foreign_key="product.id", nullable=True
    )
    quantity: int = Field(nullable=False)
    unit_cost: Decimal = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 2), nullable=False)
    )
    total: Decimal = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 2), nullable=False)
    )
    barcode: Optional[str] = Field(nullable=True)
    product_name: Optional[str] = Field(nullable=True)
    unit_com: Optional[str] = Field(nullable=True)
