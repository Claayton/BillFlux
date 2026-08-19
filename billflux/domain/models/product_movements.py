"""Module for named tuple, product movement model"""

from collections import namedtuple

ProductMovement = namedtuple(
    "ProductMovement",
    [
        "id",
        "product_id",
        "movement_type",
        "quantity",
        "obs",
        "created_at",
    ],
)
