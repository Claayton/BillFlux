"""Module for model Order (pedidos do PDV)"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import SQLModel, Field


class Order(SQLModel, table=True):
    """Vendas fechadas no PDV"""

    __tablename__ = "orders"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    total: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    payment_method_id: Optional[int] = Field(
        default=None, foreign_key="paymentmethod.id", nullable=False
    )
    obs: Optional[str] = Field(nullable=True)
