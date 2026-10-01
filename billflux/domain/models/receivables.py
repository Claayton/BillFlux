"""Module for named tuple, receivable models (fiado/crediário)"""

from collections import namedtuple

Receivable = namedtuple(
    "Receivable",
    [
        "id",
        "order_id",
        "customer_id",
        "customer_name",
        "amount",
        "paid_amount",
        "cancelled",
        "obs",
        "created_at",
    ],
)

ReceivablePayment = namedtuple(
    "ReceivablePayment",
    [
        "id",
        "receivable_id",
        "method_id",
        "amount",
        "cash_movement_id",
        "created_by",
        "created_at",
    ],
)
