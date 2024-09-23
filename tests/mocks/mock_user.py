"""File form mock user"""

from collections import namedtuple
from faker import Faker
from billflux.security import PasswordHash


fake = Faker()
password_hash = PasswordHash()


UserMock = namedtuple(
    "User",
    [
        "id",
        "name",
        "email",
        "password",
        "password_hash",
        "secundary_id",
        "is_staff",
        "is_active",
        "last_login",
        "date_joined",
    ],
)


def mock_user():
    """Mock para users"""

    password = fake.password()

    return UserMock(
        id=fake.random_number(),
        name=fake.name(),
        email=fake.email(),
        password=password,
        password_hash=password_hash.hash(password).decode(),
        secundary_id=fake.random_number(),
        is_staff=False,
        is_active=False,
        last_login=fake.date_time(),
        date_joined=fake.date_time(),
    )
