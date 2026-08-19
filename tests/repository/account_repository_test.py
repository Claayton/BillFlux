"""Tests for the AccountRepository Class"""

from billflux.infra.repository.account_repository import AccountRepository
from billflux.infra.repository.bill_repository import BillRepository


def test_insert_account(account_repository):
    """Inserting a category should persist it and return its data."""

    account = account_repository.insert_account(name="Energia", type="despesa")

    assert account.id is not None
    assert account.name == "Energia"
    assert account.type == "despesa"
    assert account.parent_id is None
    assert account.active is True

    fetched = account_repository.get_account(account.id)
    assert fetched.name == "Energia"


def test_get_accounts(account_repository):
    """get_accounts should return the created categories."""

    account_repository.insert_account(name="Água", type="despesa")
    accounts = account_repository.get_accounts()

    assert any(a.name == "Água" for a in accounts)


def test_update_account(account_repository):
    """Updating a category should change its fields."""

    account = account_repository.insert_account(name="Antes", type="despesa")
    updated = account_repository.update_account(account.id, name="Depois")

    assert updated.name == "Depois"
    assert account_repository.get_account(account.id).name == "Depois"


def test_delete_account(account_repository):
    """Deleting an unused category should remove it."""

    account = account_repository.insert_account(name="Temporária", type="despesa")
    assert account_repository.delete_account(account.id) is True
    assert account_repository.get_account(account.id) is None


def test_count_children(account_repository):
    """count_children should return the number of subcategories."""

    parent = account_repository.insert_account(name="Principal", type="despesa")
    account_repository.insert_account(name="Filha", type="despesa", parent_id=parent.id)

    assert account_repository.count_children(parent.id) == 1


def test_count_bills(account_repository):
    """count_bills should return how many bills use the category."""

    account = account_repository.insert_account(name="Impostos", type="despesa")
    BillRepository().insert_bill(
        value=50, due_date=None, reference="DAS", account_id=account.id
    )

    assert account_repository.count_bills(account.id) == 1
