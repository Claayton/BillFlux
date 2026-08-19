"""Module for model PaymentMethod (formas de pagamento)"""

from typing import Optional

from sqlmodel import SQLModel, Field


class PaymentMethod(SQLModel, table=True):
    """Formas de pagamento usadas no PDV (modular)"""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    active: bool = Field(default=True)
    sort_order: int = Field(default=0)
