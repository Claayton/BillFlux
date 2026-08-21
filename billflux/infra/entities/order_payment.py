"""Module for model OrderPayment (pagamentos de um pedido)"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import SQLModel, Field


class OrderPayment(SQLModel, table=True):
    """Valor recebido por forma de pagamento num pedido (pagamento dividido)"""

    __tablename__ = "order_payments"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: Optional[int] = Field(
        default=None, foreign_key="orders.id", nullable=False
    )
    payment_method_id: Optional[int] = Field(
        default=None, foreign_key="paymentmethod.id", nullable=False
    )
    amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
