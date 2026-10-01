"""Module for named tuples, comandas (tabs) domain models"""

from collections import namedtuple

Tab = namedtuple(
    "Tab",
    [
        "id",
        "number",
        "identification",
        "status",
        "subtotal",
        "discount",
        "total",
        "order_id",
        "print_count",
        "opened_at",
        "closed_at",
        "canceled_at",
        "opened_by",
        "closed_by",
        "canceled_by",
        "created_at",
        "updated_at",
    ],
)

TabItem = namedtuple(
    "TabItem",
    [
        "id",
        "tab_id",
        "product_id",
        "unit_id",
        "name",
        "quantity",
        "unit_price",
        "total",
        "factor",
        "created_at",
        "updated_at",
    ],
)
