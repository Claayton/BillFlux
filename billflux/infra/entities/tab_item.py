"""Module for model TabItem (itens da comanda)"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import Field, SQLModel


class TabItem(SQLModel, table=True):
    """Item da comanda, com snapshot de nome/preço do momento do lançamento."""

    __tablename__ = "tab_item"

    id: Optional[int] = Field(default=None, primary_key=True)
    tab_id: Optional[int] = Field(default=None, foreign_key="tab.id", nullable=False)
    product_id: Optional[int] = Field(
        default=None, foreign_key="product.id", nullable=False
    )
    unit_id: Optional[int] = Field(default=None, nullable=True)
    name: str = Field(nullable=False)
    quantity: int = Field(nullable=False)
    unit_price: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    total: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    factor: int = Field(default=1, nullable=False)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.now, nullable=False)
