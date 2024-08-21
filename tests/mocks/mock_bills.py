"""Module for mock bills"""

from collections import namedtuple
from faker import Faker


fake = Faker()

BillMock = namedtuple(
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
    ],
)


def mock_bill():

    return BillMock(
        id=fake.random_number(),
        status=fake.boolean(),
        due_date=fake.date_time(),
        value=fake.pricetag(),
        reference=fake.text(),
        suplyer=fake.name(),
        bill_type=fake.name(),
        days=fake.random_number(),
        payday=fake.date_time(),
        value_from_payment=fake.pricetag(),
        bar_code=fake.random_number(),
        obs=fake.text(),
        date_from_add=fake.date_time(),
    )
