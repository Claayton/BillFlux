"""Module for model Account (plano de contas)"""

from typing import Optional

from sqlmodel import SQLModel, Field


class Account(SQLModel, table=True):
    """Categorias do plano de contas (receitas e despesas)"""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    type: str = Field(default="despesa")
    parent_id: Optional[int] = Field(
        default=None, foreign_key="account.id", nullable=True
    )
    color: Optional[str] = Field(default=None, nullable=True)
    active: bool = Field(default=True)
