"""Instance from Bill table and yours methods"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .users import User


class Bill(SQLModel, table=True):
    """Bills table"""

    id: Optional[int] = Field(primary_key=True, default=None, nullable=True)
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

    user_id: int = Field(foreign_key="user.id", primary_key=True, nullable=False)

    user: "User" = Relationship(back_populates="bill")

    def __repr__(self):
        return f"<Bill {self.id}: {self.user.name}>"
