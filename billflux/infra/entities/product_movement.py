"""Module for model ProductMovement (log de estoque)"""

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class ProductMovement(SQLModel, table=True):
    """Movimentações de estoque (entrada, saída ou ajuste)"""

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: Optional[int] = Field(
        default=None, foreign_key="product.id", nullable=False
    )
    movement_type: str = Field(nullable=False)
    quantity: int = Field(nullable=False)
    obs: Optional[str] = Field(nullable=True)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
