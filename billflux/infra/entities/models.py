"""Module for model Bill"""

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class Bill(SQLModel, table=True):

    id: Optional[int] = Field(primary_key=True, default=None, nullable=False)
    bar_code: int
    suplyer: str
    type: str
    due_date: datetime = Field(default=None, nullable=True)
    payday: datetime = Field(default=None, nullable=True)
    is_paid_out: bool = Field(default=None, nullable=True)
