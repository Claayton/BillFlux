"""Module for model PurchaseOrder (compras de produtos)"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import SQLModel, Field


class PurchaseOrder(SQLModel, table=True):
    """Compras de mercadorias (entradas no estoque)"""

    __tablename__ = "purchase_order"

    id: Optional[int] = Field(default=None, primary_key=True)
    nf_number: Optional[str] = Field(default=None, nullable=True)
    nf_serie: Optional[str] = Field(default=None, nullable=True)
    nf_chave: Optional[str] = Field(default=None, nullable=True)
    nf_modelo: Optional[str] = Field(default=None, nullable=True)
    supplier_id: Optional[int] = Field(
        default=None, foreign_key="supplier.id", nullable=True
    )
    total: Decimal = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 2), nullable=False)
    )
    freight: Decimal = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 2), nullable=False)
    )
    discount: Decimal = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 2), nullable=False)
    )
    net_total: Decimal = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 2), nullable=False)
    )
    status: str = Field(default="rascunho", nullable=False)
    bill_id: Optional[int] = Field(default=None, foreign_key="bill.id", nullable=True)
    due_date: Optional[datetime] = Field(nullable=True)
    obs: Optional[str] = Field(nullable=True)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
