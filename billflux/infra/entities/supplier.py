"""Module for model Supplier (fornecedores)"""

from typing import Optional

from sqlmodel import SQLModel, Field


class Supplier(SQLModel, table=True):
    """Cadastro de fornecedores"""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, index=True)
    cnpj: Optional[str] = Field(default=None, nullable=True, index=True)
    phone: Optional[str] = Field(default=None, nullable=True)
    email: Optional[str] = Field(default=None, nullable=True)
    contact: Optional[str] = Field(default=None, nullable=True)
    address: Optional[str] = Field(default=None, nullable=True)
    city: Optional[str] = Field(default=None, nullable=True)
    state: Optional[str] = Field(default=None, nullable=True)
    neighborhood: Optional[str] = Field(default=None, nullable=True)
    obs: Optional[str] = Field(default=None, nullable=True)
    active: bool = Field(default=True, nullable=False)
