"""Module for named tuple, bill model"""

from collections import namedtuple

Bill = namedtuple(
    "Bill",
    [
        "id",
        "status",
        "due_date",
        "value",
        "reference",
        "suplyer",
        "supplier_id",
        "bill_type",
        "days",
        "payday",
        "value_from_payment",
        "bar_code",
        "pix_key",
        "pix_payload",
        "pix_image",
        "obs",
        "account_id",
        "date_from_add",
    ],
)
