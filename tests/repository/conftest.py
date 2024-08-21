"""Conftest for tests/repository"""

from pytest import fixture
from billflux.infra.repository.bill_repository import BillRepository


@fixture
def bill_repository():  # pylint: disable=W0621
    """Fixture para montar o objeto UserRepository"""

    return BillRepository()
