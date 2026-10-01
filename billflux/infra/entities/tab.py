"""Module for model Tab (comandas do PDV)"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import Field, SQLModel, UniqueConstraint


class Tab(SQLModel, table=True):
    """Comanda: venda temporariamente estacionada no PDV.

    Não é uma `orders`: só vira venda de fato ao fechar (cria o pedido
    vinculado em `order_id`), assim relatórios/faturamento não contam
    comandas abertas.
    """

    __tablename__ = "tab"
    __table_args__ = (UniqueConstraint("number", name="uq_tab_number"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    number: int = Field(nullable=False)
    identification: str = Field(nullable=False)
    status: str = Field(default="open", nullable=False)
    subtotal: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(10, 2), nullable=False),
    )
    discount: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(10, 2), nullable=True),
    )
    total: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(10, 2), nullable=False),
    )
    order_id: Optional[int] = Field(
        default=None, foreign_key="orders.id", nullable=True
    )
    print_count: int = Field(default=0, nullable=False)
    opened_at: datetime = Field(default_factory=datetime.now, nullable=False)
    closed_at: Optional[datetime] = Field(default=None, nullable=True)
    canceled_at: Optional[datetime] = Field(default=None, nullable=True)
    opened_by: Optional[str] = Field(default=None, nullable=True)
    closed_by: Optional[str] = Field(default=None, nullable=True)
    canceled_by: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.now, nullable=False)
