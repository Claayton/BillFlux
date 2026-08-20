"""Tests for the payment methods JSON API (SPA)."""


def _csrf(client):
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    return response.get_json()["csrf_token"]


def test_payments_requires_login(client):
    """Sem sessão, /api/payments deve devolver 401 JSON."""

    assert client.get("/api/payments").status_code == 401


def test_payments_list(logged_client):
    """Lista devolve as formas de pagamento com as padrão."""

    response = logged_client.get("/api/payments")

    assert response.status_code == 200
    methods = response.get_json()["methods"]
    assert any(m["name"] == "Dinheiro" for m in methods)


def test_payments_create(logged_client):
    """POST cadastra uma nova forma de pagamento."""

    token = _csrf(logged_client)
    response = logged_client.post(
        "/api/payments",
        json={"name": "Boleto"},
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 201
    methods = response.get_json()["methods"]
    assert any(m["name"] == "Boleto" for m in methods)


def test_payments_create_duplicate(logged_client):
    """POST com nome repetido deve devolver 400."""

    token = _csrf(logged_client)
    dup = logged_client.post(
        "/api/payments",
        json={"name": "Dinheiro"},
        headers={"X-CSRFToken": token},
    )
    assert dup.status_code == 400


def test_payments_create_validation(logged_client):
    """POST sem nome deve devolver 400."""

    token = _csrf(logged_client)
    missing = logged_client.post(
        "/api/payments", json={"name": ""}, headers={"X-CSRFToken": token}
    )
    assert missing.status_code == 400


def test_payments_toggle(logged_client):
    """POST /toggle ativa e desativa a forma."""

    token = _csrf(logged_client)
    created = logged_client.post(
        "/api/payments",
        json={"name": "Cripto"},
        headers={"X-CSRFToken": token},
    ).get_json()
    method = next(m for m in created["methods"] if m["name"] == "Cripto")

    response = logged_client.post(
        f"/api/payments/{method['id']}/toggle", headers={"X-CSRFToken": token}
    )
    assert response.status_code == 200
    toggled = next(m for m in response.get_json()["methods"] if m["id"] == method["id"])
    assert toggled["active"] is False


def test_payments_delete(logged_client):
    """DELETE remove uma forma não utilizada."""

    token = _csrf(logged_client)
    created = logged_client.post(
        "/api/payments",
        json={"name": "Remover"},
        headers={"X-CSRFToken": token},
    ).get_json()
    method = next(m for m in created["methods"] if m["name"] == "Remover")

    response = logged_client.delete(
        f"/api/payments/{method['id']}", headers={"X-CSRFToken": token}
    )
    assert response.status_code == 200
    assert not any(m["id"] == method["id"] for m in response.get_json()["methods"])

    missing = logged_client.delete(
        "/api/payments/999999", headers={"X-CSRFToken": token}
    )
    assert missing.status_code == 404
