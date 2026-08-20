"""Tests for the accounts (plano de contas) JSON API (SPA)."""


def _csrf(client):
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    return response.get_json()["csrf_token"]


def test_accounts_requires_login(client):
    """Sem sessão, /api/accounts deve devolver 401 JSON."""

    assert client.get("/api/accounts").status_code == 401


def test_accounts_list(logged_client):
    """Lista devolve seções de receitas e despesas."""

    response = logged_client.get("/api/accounts")

    assert response.status_code == 200
    sections = response.get_json()["sections"]
    assert {s["type"] for s in sections} == {"receita", "despesa"}


def test_accounts_create_and_edit(logged_client):
    """POST cria categoria e PUT a edita."""

    token = _csrf(logged_client)
    created = logged_client.post(
        "/api/accounts",
        json={"name": "Nova despesa", "type": "despesa"},
        headers={"X-CSRFToken": token},
    )

    assert created.status_code == 201
    group = _find_group(created.get_json(), "Nova despesa")
    account_id = group["account"]["id"]

    edited = logged_client.put(
        f"/api/accounts/{account_id}",
        json={"name": "Despesa editada", "type": "despesa"},
        headers={"X-CSRFToken": token},
    )
    assert edited.status_code == 200
    assert (
        _find_group(edited.get_json(), "Despesa editada")["account"]["id"] == account_id
    )


def test_accounts_create_subcategory(logged_client):
    """POST com parent_id cria uma subcategoria."""

    token = _csrf(logged_client)
    sections = logged_client.get("/api/accounts").get_json()["sections"]
    receita = sections[0]["groups"][0]["account"]
    parent_id = receita["id"]

    response = logged_client.post(
        "/api/accounts",
        json={"name": "Sub Vendas", "type": "receita", "parent_id": parent_id},
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 201
    parent = _find_group(response.get_json(), receita["name"])
    assert any(c["name"] == "Sub Vendas" for c in parent["children"])


def test_accounts_validation(logged_client):
    """POST sem nome ou tipo inválido deve devolver 400."""

    token = _csrf(logged_client)
    missing = logged_client.post(
        "/api/accounts", json={"name": ""}, headers={"X-CSRFToken": token}
    )
    assert missing.status_code == 400

    invalid = logged_client.post(
        "/api/accounts",
        json={"name": "X", "type": "outro"},
        headers={"X-CSRFToken": token},
    )
    assert invalid.status_code == 400


def test_accounts_delete_blocked_with_children(logged_client):
    """DELETE de categoria com subcategorias deve devolver 400."""

    token = _csrf(logged_client)
    created = logged_client.post(
        "/api/accounts",
        json={"name": "Pai", "type": "despesa"},
        headers={"X-CSRFToken": token},
    ).get_json()
    parent_id = _find_group(created, "Pai")["account"]["id"]
    logged_client.post(
        "/api/accounts",
        json={"name": "Filho", "type": "despesa", "parent_id": parent_id},
        headers={"X-CSRFToken": token},
    )

    response = logged_client.delete(
        f"/api/accounts/{parent_id}", headers={"X-CSRFToken": token}
    )
    assert response.status_code == 400


def test_accounts_delete(logged_client):
    """DELETE remove uma categoria livre."""

    token = _csrf(logged_client)
    created = logged_client.post(
        "/api/accounts",
        json={"name": "Remover", "type": "despesa"},
        headers={"X-CSRFToken": token},
    ).get_json()
    account_id = _find_group(created, "Remover")["account"]["id"]

    response = logged_client.delete(
        f"/api/accounts/{account_id}", headers={"X-CSRFToken": token}
    )
    assert response.status_code == 200
    assert _find_group(response.get_json(), "Remover") is None


def _find_group(payload, name):
    for section in payload["sections"]:
        for group in section["groups"]:
            if group["account"]["name"] == name:
                return group
    return None
