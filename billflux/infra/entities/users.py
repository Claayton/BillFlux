"""Instance from User table and your methods"""

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field, Relationship
from billflux.extensions.auth import lm

if TYPE_CHECKING:
    from .tokens import Token
    from .bills import Bill


@lm.user_loader
def load_user(user_id):
    """Load one user"""
    return User.query.filter_by(id=user_id).first()


class User(SQLModel, UserMixin, table=True):
    """Table from users"""

    __table_args__ = (UniqueConstraint("email"),)

    id: Optional[int] = Field(primary_key=True, default=None, nullable=False)
    name: str
    email: str
    password_hash: str

    secundary_id: int = 0
    is_staff: bool
    is_active: bool
    last_login: datetime
    date_joined: datetime

    token: List["Token"] = Relationship(back_populates="user")
    bill: List["Bill"] = Relationship(back_populates="user")

    def __repr__(self):
        return f"<User {self.name}>"
