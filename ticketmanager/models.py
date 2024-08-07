from typing import Optional
from sqlmodel import SQLModel, select, Field
from datetime import datetime


class Tickets(SQLModel, table=True):

    id: Optional[int] = Field(primary_key=True, default=None, nullable=False)
    bar_code: int
    type: str
    suplyer: str
    due_date: datetime
    payday: datetime
    is_paid_out: bool
