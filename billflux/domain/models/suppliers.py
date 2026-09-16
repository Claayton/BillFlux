"""Module for named tuple, supplier model"""

from collections import namedtuple

Supplier = namedtuple(
    "Supplier",
    [
        "id",
        "name",
        "cnpj",
        "phone",
        "email",
        "contact",
        "address",
        "city",
        "state",
        "neighborhood",
        "obs",
        "active",
    ],
)
