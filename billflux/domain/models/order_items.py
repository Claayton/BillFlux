"""Module for named tuple, order item model"""

from collections import namedtuple

OrderItem = namedtuple(
    "OrderItem",
    [
        "id",
        "order_id",
        "product_id",
        "quantity",
        "unit_price",
    ],
)
