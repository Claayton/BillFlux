"""Module for model Bill"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Bill(SQLModel, table=True):
    """Bills table"""

    id: Optional[int] = Field(default=None, primary_key=True)
    status: bool = Field(default=False)
    due_date: datetime = Field(nullable=True)
    value: Optional[int] = Field(nullable=True)
    reference: Optional[str] = Field(nullable=True)
    suplyer: Optional[str] = Field(nullable=True)
    bill_type: Optional[str] = Field(nullable=True)
    days: Optional[int] = Field(nullable=True)
    payday: Optional[datetime] = Field(nullable=True)
    value_from_payment: Optional[int] = Field(nullable=True)
    bar_code: Optional[int] = Field(nullable=True)
    obs: Optional[str] = Field(nullable=True)
    date_from_add: datetime = Field(nullable=False)
