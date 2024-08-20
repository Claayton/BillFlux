from collections import namedtuple

Ticket = namedtuple(
    "Ticket",
    ["id", "bar_code", "suplyer", "type", "due_date", "payday", "is_paid_out"],
)
