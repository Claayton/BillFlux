"""Tests from the chart of accounts routes"""

import re

from billflux.infra.repository.account_repository import AccountRepository
from billflux.infra.repository.bill_repository import BillRepository


def _get_csrf_token(client):
    """Fetch the CSRF token from the accounts page form."""
    response = client.get("/accounts/")
    match = re.search(
        r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)
    )
    assert match, "CSRF token not found in /accounts/ page"
    return match.group(1)


def _create_account(name="Energia de teste", type_="despesa", parent_id=None):
    return AccountRepository().insert_account(
        name=name, type=type_, parent_id=parent_id
    )


def test_accounts_page(logged_client):
    """GET /accounts should render the page with seeded categories."""

    response = logged_client.get("/accounts")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Plano de contas" in page
    assert "Receitas" in page
    assert "Despesas" in page
    assert "Vendas" in page
    assert "Aluguel" in page


def test_accounts_requires_login(client):
    """Unauthenticated users should be redirected to login."""

    response = client.get("/accounts")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_new_account(logged_client):
    """POSTing to /accounts/new should create the category."""

    token = _get_csrf_token(logged_client)
    response = logged_client.post(
        "/accounts/new",
        data={
            "csrf_token": token,
            "name": "Transporte",
            "type": "despesa",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert any(a.name == "Transporte" for a in AccountRepository().get_accounts())


def test_new_account_requires_name(logged_client):
    """Creating a category without a name should not persist it."""

    token = _get_csrf_token(logged_client)
    logged_client.post(
        "/accounts/new",
        data={"csrf_token": token, "name": "", "type": "despesa"},
        follow_redirects=True,
    )

    assert not any(a.name == "" for a in AccountRepository().get_accounts())


def test_edit_account(logged_client):
    """POSTing to /accounts/edit should update the category."""

    account = _create_account()
    token = _get_csrf_token(logged_client)
    response = logged_client.post(
        "/accounts/edit",
        data={
            "csrf_token": token,
            "account_id": str(account.id),
            "name": "Energia atualizada",
            "type": "despesa",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert AccountRepository().get_account(account.id).name == "Energia atualizada"


def test_delete_account(logged_client):
    """Deleting an unused category should remove it."""

    account = _create_account(name="Excluir-me")
    token = _get_csrf_token(logged_client)

    response = logged_client.post(
        f"/accounts/delete/{account.id}",
        headers={"X-CSRFToken": token},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert AccountRepository().get_account(account.id) is None


def test_delete_account_in_use_blocked(logged_client):
    """Deleting a category linked to bills should be blocked."""

    account = _create_account(name="Em uso")
    BillRepository().insert_bill(
        value=10, due_date=None, reference="Conta", account_id=account.id
    )
    token = _get_csrf_token(logged_client)

    response = logged_client.post(
        f"/accounts/delete/{account.id}",
        headers={"X-CSRFToken": token},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "contas vinculadas" in response.get_data(as_text=True)
    assert AccountRepository().get_account(account.id) is not None


def test_delete_account_with_children_blocked(logged_client):
    """Deleting a category with subcategories should be blocked."""

    parent = _create_account(name="Pai")
    _create_account(name="Filho", parent_id=parent.id)
    token = _get_csrf_token(logged_client)

    response = logged_client.post(
        f"/accounts/delete/{parent.id}",
        headers={"X-CSRFToken": token},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "subcategorias" in response.get_data(as_text=True)
    assert AccountRepository().get_account(parent.id) is not None
