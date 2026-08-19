"""Module for named tuple, order model"""

from collections import namedtuple

Order = namedtuple(
    "Order",
    [
        "id",
        "created_at",
        "total",
        "payment_method_id",
        "obs",
    ],
)
