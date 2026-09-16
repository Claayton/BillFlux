"""Module for named tuple, customer model"""

from collections import namedtuple

Customer = namedtuple(
    "Customer",
    [
        "id",
        "name",
        "cpf_cnpj",
        "phone",
        "email",
        "address",
        "city",
        "state",
        "neighborhood",
        "complement",
        "number",
        "zip_code",
        "obs",
        "active",
    ],
)
