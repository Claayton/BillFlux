"""Module for model Setting (configurações editáveis via tela)"""

from typing import Optional

from sqlmodel import SQLModel, Field


class Setting(SQLModel, table=True):
    """Par chave-valor de configuração (lido pela API de settings)"""

    __tablename__ = "setting"

    key: str = Field(primary_key=True, max_length=120)
    value: Optional[str] = Field(default=None, nullable=True)
