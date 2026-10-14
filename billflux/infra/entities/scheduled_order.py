"""Módulo para model ScheduledOrder (encargos/agenda de pedidos a clientes)"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Date, Numeric
from sqlmodel import SQLModel, Field


class ScheduledOrder(SQLModel, table=True):
    """Pedido futuro de un cliente (retirar/entregar), con fecha, hora y status.

    Los ítems se guardan como JSON en ``items``::
        [{"product_id": 1, "name": "Gelo 5kg", "quantity": 2,
          "unit_price": "30.00", "total": "60.00"}]
    """

    __tablename__ = "scheduled_order"

    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: Optional[int] = Field(
        default=None, foreign_key="customer.id", nullable=True, index=True
    )
    customer_name: Optional[str] = Field(default=None, nullable=True)
    order_date: Optional[date] = Field(default=None, sa_column=Column(Date, index=True))
    order_time: Optional[str] = Field(default=None, nullable=True)
    status: str = Field(default="pendente", nullable=False, index=True)
    obs: Optional[str] = Field(default=None, nullable=True)
    total: Optional[Decimal] = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 2), nullable=False)
    )
    items: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
