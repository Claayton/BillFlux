"""Module for named tuple, payment method model"""

from collections import namedtuple

PaymentMethod = namedtuple(
    "PaymentMethod",
    [
        "id",
        "name",
        "active",
        "sort_order",
    ],
)
