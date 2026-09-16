"""Module for named tuple, purchase item model"""

from collections import namedtuple

PurchaseItem = namedtuple(
    "PurchaseItem",
    [
        "id",
        "purchase_id",
        "product_id",
        "product_name",
        "quantity",
        "unit_cost",
        "total",
        "barcode",
        "unit_com",
    ],
)
