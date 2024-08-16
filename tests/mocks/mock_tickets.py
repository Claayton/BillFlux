from faker import Faker
from collections import namedtuple


fake = Faker()

TicketMock = namedtuple(
    "Ticket",
    ["id", "bar_code", "suplyer", "type", "due_date", "payday", "is_paid_out"],
)


def mock_ticket():

    return TicketMock(
        id=fake.random_number(),
        bar_code=fake.random_number(),
        suplyer=fake.name(),
        type=fake.name(),
        due_date=fake.date_time(),
        payday=fake.date_time(),
        is_paid_out=False,
    )
