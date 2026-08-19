"""Module for model Sale (vendas diárias)"""

import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import SQLModel, Field


class Sale(SQLModel, table=True):
    """Vendas do dia (total bruto)"""

    id: Optional[int] = Field(default=None, primary_key=True)
    date: datetime.date = Field(nullable=False, unique=True)
    total: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    obs: Optional[str] = Field(nullable=True)
