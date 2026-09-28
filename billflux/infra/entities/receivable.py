"""Module for model Receivable (contas a receber / fiado)"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import SQLModel, Field


class Receivable(SQLModel, table=True):
    """Débito de cliente (fiado/crediário) gerado por uma venda."""

    __tablename__ = "receivable"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: Optional[int] = Field(
        default=None, foreign_key="orders.id", nullable=True
    )
    customer_id: int = Field(default=None, foreign_key="customer.id", nullable=False)
    amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    paid_amount: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(10, 2), nullable=False),
    )
    cancelled: bool = Field(default=False, nullable=False)
    obs: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
