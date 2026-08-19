"""Model for repository to User"""

from datetime import datetime
from typing import Optional

from sqlmodel import select

from billflux.infra.config.database import get_session
from billflux.infra.entities.user import User


class UserRepository:
    """User table data manipulation"""

    def create_user(self, username: str, password_hash: str, email: str = None) -> User:
        """Creates a new user and returns it."""
        session = get_session()
        try:
            with session:
                user = User(
                    username=username,
                    email=email,
                    password_hash=password_hash,
                    created_at=datetime.now(),
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                return user
        finally:
            session.close()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Finds a user by username."""
        session = get_session()
        try:
            with session:
                sql = select(User).where(User.username == username)
                return session.exec(sql).one_or_none()
        finally:
            session.close()
