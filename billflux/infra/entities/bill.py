"""Module for model Bill"""

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class Bill(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True)
    status: bool = Field(default=False)
    due_date: datetime = Field(default_factory=lambda: datetime.now(), nullable=False)
    value: Optional[int] = Field(default=None, nullable=True)
    reference: Optional[str] = Field(default=None, nullable=True)
    suplyer: Optional[str] = Field(default=None, nullable=True)
    bill_type: Optional[str] = Field(default=None, nullable=True)
    days: Optional[int] = Field(default=None, nullable=True)
    payday: Optional[datetime] = Field(default=None, nullable=True)
    value_from_payment: Optional[int] = Field(default=None, nullable=True)
    bar_code: Optional[int] = Field(default=None, nullable=True)
    obs: Optional[str] = Field(default=None, nullable=True)
    date_from_add: datetime = Field(
        default_factory=lambda: datetime.now(), nullable=False
    )
