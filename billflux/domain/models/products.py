"""Module for named tuple, product model"""

from collections import namedtuple

Product = namedtuple(
    "Product",
    [
        "id",
        "name",
        "price",
        "cost",
        "barcode",
        "secondary_code",
        "category",
        "suppliers",
        "stock_quantity",
        "min_stock",
        "active",
        "obs",
    ],
)
