"""Module for named tuple, category model"""

from collections import namedtuple

Category = namedtuple(
    "Category",
    [
        "id",
        "name",
        "active",
    ],
)
