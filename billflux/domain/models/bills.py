"""Module for named tuple, bill model"""

from collections import namedtuple

Bill = namedtuple(
    "Bill",
    ["id", "bar_code", "suplyer", "type", "due_date", "payday", "is_paid_out"],
)
