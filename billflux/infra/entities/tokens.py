"""Instance from Token table and yours methods"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .users import User


class Token(SQLModel, table=True):
    """Table from tokens"""

    id: Optional[int] = Field(primary_key=True, default=None, nullable=False)
    token: str
    expiration: datetime

    user_id: int = Field(foreign_key="user.id", primary_key=True, nullable=False)

    user: "User" = Relationship(back_populates="token")

    def __repr__(self):
        return f"<Token {self.id}: {self.user.name}>"
