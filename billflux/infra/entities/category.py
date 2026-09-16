"""Module for model Category (categorias de produtos)"""

from typing import Optional

from sqlmodel import SQLModel, Field


class Category(SQLModel, table=True):
    """Categorias usadas para agrupar os produtos"""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    active: bool = Field(default=True)
