"""Instance from User table and your methods"""

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field, Relationship


if TYPE_CHECKING:
    from .bills import Bill


class User(SQLModel, UserMixin, table=True):
    """Table from users"""

    __table_args__ = (UniqueConstraint("email"),)

    id: Optional[int] = Field(primary_key=True, default=None, nullable=False)
    name: str
    email: str
    password_hash: str

    secundary_id: int = 0
    is_staff: bool
    is_active_user: bool
    last_login: datetime
    date_joined: datetime

    bill: List["Bill"] = Relationship(back_populates="user")

    def __repr__(self):
        return f"<User {self.name}>"
