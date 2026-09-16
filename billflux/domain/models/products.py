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
        "category_id",
        "category_name",
        "suppliers",
        "supplier_id",
        "supplier_name",
        "stock_quantity",
        "min_stock",
        "ideal_stock",
        "active",
        "obs",
    ],
)
