from typing import Optional, List
from datetime import datetime
from sqlmodel import select
from ticketmanager.infra.config.database import get_session
from ticketmanager.infra.entities.models import Ticket as TicketModel
from ticketmanager.domain.models.tickets import Ticket


class TicketRepository:
    """Manipulação de dados da tabela Ticket"""

    def __init__(self) -> None:
        self.__session = get_session()

    def insert_ticket(
        self,
        bar_code: int,
        suplyer: str,
        type: str,
        due_date: datetime = None,
        payday: datetime = None,
        is_paid_out: bool = None,
    ) -> Ticket:

        with self.__session as session:

            ticket = TicketModel(bar_code=bar_code, type=type, suplyer=suplyer)

            session.add(ticket)
            session.commit()
            session.refresh(ticket)

            return Ticket(**dict(ticket))

    def get_tickets(self) -> List[Ticket]:

        with self.__session as session:
            sql = select(Ticket)
            return list(session.exec(sql))
