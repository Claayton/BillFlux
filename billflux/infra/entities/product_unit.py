"""Module for ProductUnit (apresentações de produto: unidade, caixa, etc.)"""

from typing import Optional
from decimal import Decimal

from sqlmodel import SQLModel, Field


class ProductUnit(SQLModel, table=True):
    """Apresentação de produto — unidade, caixa 12, caixa 15, etc."""

    __tablename__ = "product_unit"

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id", nullable=False, index=True)
    name: str = Field(nullable=False, max_length=80)
    barcode: Optional[str] = Field(default=None, max_length=60, unique=True)
    factor: int = Field(nullable=False, default=1)
    price: Decimal = Field(default=Decimal("0"), max_digits=10, decimal_places=2)
    is_default: bool = Field(default=False)
