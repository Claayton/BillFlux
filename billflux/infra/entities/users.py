"""Instance from User table and your methods"""

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .tokens import Token
    from .bills import Bill


class User(SQLModel, table=True):
    """Table from users"""

    __table_args__ = (UniqueConstraint("email", "username"),)

    id: Optional[int] = Field(primary_key=True, default=None, nullable=False)
    name: str
    email: str
    username: str
    password_hash: str

    secundary_id: int = 0
    is_staff: bool
    is_active_user: bool
    last_login: datetime
    date_joined: datetime

    token: List["Token"] = Relationship(back_populates="user")
    bill: List["Bill"] = Relationship(back_populates="user")

    def __repr__(self):
        return f"<User {self.name}>"
