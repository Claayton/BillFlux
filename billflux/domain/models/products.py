"""Module for named tuple, product model"""

from collections import namedtuple

Product = namedtuple(
    "Product",
    [
        "id",
        "name",
        "price",
        "barcode",
        "stock_quantity",
        "min_stock",
        "active",
        "obs",
    ],
)
