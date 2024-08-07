from typing import Optional, List
from datetime import datetime
from sqlmodel import select
from ticketmanager.database import get_session
from ticketmanager.models import Ticket


def add_ticket_to_database(
    bar_code: int,
    suplyer: str,
    type: str,
    due_date: datetime = None,
    payday: datetime = None,
    is_paid_out: bool = None,
) -> bool:

    with get_session() as session:
        ticket = Ticket(bar_code=bar_code, type=type, suplyer=suplyer)

    session.add(ticket)
    session.commit()
    return True


def get_tickets_from_database() -> List[Ticket]:

    with get_session() as session:
        sql = select(Ticket)
        return list(session.exec(sql))
