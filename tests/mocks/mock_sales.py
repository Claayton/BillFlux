"""Module for mock sales"""

from collections import namedtuple
from faker import Faker

fake = Faker()

SaleMock = namedtuple(
    "Sale",
    [
        "id",
        "date",
        "total",
        "obs",
    ],
)


def mock_sale():

    return SaleMock(
        id=fake.random_number(),
        date=fake.date_this_year(),
        total=fake.pydecimal(left_digits=4, right_digits=2, positive=True),
        obs=fake.text(),
    )
