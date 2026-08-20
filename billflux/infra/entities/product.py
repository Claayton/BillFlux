"""Module for model Product (catálogo do PDV)"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import SQLModel, Field


class Product(SQLModel, table=True):
    """Produtos vendidos no PDV, com controle de estoque"""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    price: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    cost: Decimal = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 2), nullable=False)
    )
    barcode: Optional[str] = Field(default=None, unique=True, nullable=True)
    stock_quantity: int = Field(default=0, nullable=False)
    min_stock: int = Field(default=0, nullable=False)
    active: bool = Field(default=True)
    obs: Optional[str] = Field(nullable=True)
