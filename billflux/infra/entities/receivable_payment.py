"""Module for model ReceivablePayment (pagamentos de débitos de cliente)"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import SQLModel, Field


class ReceivablePayment(SQLModel, table=True):
    """Valor recebido sobre um débito (fiado) do cliente."""

    __tablename__ = "receivable_payment"

    id: Optional[int] = Field(default=None, primary_key=True)
    receivable_id: int = Field(
        default=None, foreign_key="receivable.id", nullable=False
    )
    method_id: Optional[int] = Field(
        default=None, foreign_key="paymentmethod.id", nullable=True
    )
    amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    cash_movement_id: Optional[int] = Field(
        default=None, foreign_key="cash_movement.id", nullable=True
    )
    created_by: str = Field(default="operador", nullable=False)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
