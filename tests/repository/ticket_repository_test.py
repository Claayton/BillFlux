"""Testes para a classe TicketRepository"""

from ticketmanager.infra.repository.tickets_repository import TicketRepository
from ticketmanager.infra.config.database import get_session
from ticketmanager.infra.entities.models import Ticket
from sqlmodel import select


def test_insert_ticket(fake_ticket, ticket_repository):
    """
    Testando o metodo insert_ticket()
    """

    response = ticket_repository.insert_ticket(
        bar_code=fake_ticket.bar_code,
        type=fake_ticket.type,
        suplyer=fake_ticket.suplyer,
    )

    with get_session() as session:
        query_user = session.exec(
            select(Ticket).where(Ticket.bar_code == fake_ticket.bar_code)
        ).one()

    # Testando se as informacoes enviadas pelo metodo estao no db.
    assert response.bar_code == query_user.bar_code
    assert response.type == query_user.type
    assert response.suplyer == query_user.suplyer
