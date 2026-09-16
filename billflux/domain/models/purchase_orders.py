"""Module for named tuple, purchase order model"""

from collections import namedtuple

PurchaseOrder = namedtuple(
    "PurchaseOrder",
    [
        "id",
        "nf_number",
        "nf_serie",
        "nf_chave",
        "nf_modelo",
        "supplier_id",
        "supplier_name",
        "total",
        "freight",
        "discount",
        "net_total",
        "status",
        "bill_id",
        "due_date",
        "obs",
        "created_at",
    ],
)
