"""Domain model for ProductUnit (apresentações de produto)"""

from typing import Optional
from decimal import Decimal
from collections import namedtuple

ProductUnit = namedtuple(
    "ProductUnit",
    [
        "id",
        "product_id",
        "name",
        "barcode",
        "factor",
        "price",
        "is_default",
    ],
    defaults=[None, None, None, None, 1, Decimal("0"), False],
)
