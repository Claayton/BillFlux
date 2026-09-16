"""Module for model Customer (clientes)"""

from typing import Optional

from sqlmodel import SQLModel, Field


class Customer(SQLModel, table=True):
    """Cadastro de clientes"""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, index=True)
    cpf_cnpj: Optional[str] = Field(default=None, nullable=True, index=True)
    phone: Optional[str] = Field(default=None, nullable=True)
    email: Optional[str] = Field(default=None, nullable=True)
    address: Optional[str] = Field(default=None, nullable=True)
    city: Optional[str] = Field(default=None, nullable=True)
    state: Optional[str] = Field(default=None, nullable=True)
    neighborhood: Optional[str] = Field(default=None, nullable=True)
    complement: Optional[str] = Field(default=None, nullable=True)
    number: Optional[str] = Field(default=None, nullable=True)
    zip_code: Optional[str] = Field(default=None, nullable=True)
    obs: Optional[str] = Field(default=None, nullable=True)
    active: bool = Field(default=True, nullable=False)
