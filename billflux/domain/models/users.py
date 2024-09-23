"""Module for named tuple, bill model"""

from collections import namedtuple


User = namedtuple(
    "User",
    [
        "id",
        "name",
        "email",
        "password_hash",
        "secundary_id",
        "is_staff",
        "is_active",
        "last_login",
        "date_joined",
    ],
)
