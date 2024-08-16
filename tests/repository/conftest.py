from pytest import fixture
from ticketmanager.infra.repository.tickets_repository import TicketRepository


@fixture
def ticket_repository():  # pylint: disable=W0621
    """Fixture para montar o objeto UserRepository"""

    return TicketRepository()
