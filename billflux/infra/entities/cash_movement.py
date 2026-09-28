"""Module for model CashMovement (sangria/suprimento de caixa)"""

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class CashMovement(SQLModel, table=True):
    """Movimentação avulsa de caixa (sangria ou suprimento)"""

    __tablename__ = "cash_movement"

    id: Optional[int] = Field(default=None, primary_key=True)
    cash_register_id: Optional[int] = Field(
        default=None, foreign_key="cashregister.id", nullable=False
    )
    kind: str = Field(nullable=False)  # "sangria" | "suprimento"
    amount: float = Field(nullable=False)
    obs: Optional[str] = Field(default=None, nullable=True)
    created_by: str = Field(nullable=False, default="operador")
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
