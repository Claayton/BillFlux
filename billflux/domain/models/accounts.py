"""Module for named tuple, account model"""

from collections import namedtuple

Account = namedtuple(
    "Account",
    [
        "id",
        "name",
        "type",
        "parent_id",
        "color",
        "active",
    ],
)
