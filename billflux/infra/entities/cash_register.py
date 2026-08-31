"""Module for model CashRegister (abertura/fechamento de caixa)"""

from typing import Optional

from sqlmodel import SQLModel, Field


class CashRegister(SQLModel, table=True):
    """Controle de abertura e fechamento do caixa"""

    id: Optional[int] = Field(default=None, primary_key=True)
    opened_by: str = Field(nullable=False)
    opened_at: str = Field(nullable=False)
    opening_amount: float = Field(nullable=False, default=0)
    closed_by: Optional[str] = Field(default=None, nullable=True)
    closed_at: Optional[str] = Field(default=None, nullable=True)
    closing_amount: Optional[float] = Field(default=None, nullable=True)
    expected_amount: Optional[float] = Field(default=None, nullable=True)
    status: str = Field(nullable=False, default="open")
    obs: Optional[str] = Field(default=None, nullable=True)
    # valores por forma de pagamento (JSON: {"1": 100.0, "2": 50.0})
    opening_details: Optional[str] = Field(default=None, nullable=True)
    system_totals: Optional[str] = Field(default=None, nullable=True)
    closing_details: Optional[str] = Field(default=None, nullable=True)
