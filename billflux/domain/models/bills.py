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
        "bill_type",
        "days",
        "payday",
        "value_from_payment",
        "bar_code",
        "obs",
        "date_from_add",
        "user_id",
    ],
)
