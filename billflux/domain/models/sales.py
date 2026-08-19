"""Module for named tuple, sale model"""

from collections import namedtuple

Sale = namedtuple(
    "Sale",
    [
        "id",
        "date",
        "total",
        "obs",
    ],
)
