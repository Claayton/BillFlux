"""Tests for settings, audit and cash movements JSON APIs."""


def _csrf(client):
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    return response.get_json()["csrf_token"]


def _login(client, username="admin", password="admin"):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
        headers={"X-CSRFToken": _csrf(client)},
    )


def _open_caixa(client, amount="100.00"):
    token = _csrf(client)
    response = client.post(
        "/api/caixa/open",
        json={"opening_details": {"1": amount}},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 201
    return response.get_json()


def _close_caixa(client):
    """Fecha o caixa aberto (zeros), para isolar os testes entre si."""
    status = client.get("/api/caixa").get_json()
    if not status.get("open"):
        return
    token = _csrf(client)
    response = client.post(
        "/api/caixa/close",
        json={"closing_details": {}},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200


def test_settings_get_defaults(client):
    """GET /api/settings exige login e devolve as chaves permitidas."""

    assert client.get("/api/settings").status_code == 401

    assert _login(client).status_code == 200
    data = client.get("/api/settings").get_json()["settings"]
    assert data["company.name"] == ""
    assert "secret_key" not in data


def test_settings_put_allowlist(client):
    """PUT grava só chaves permitidas; segredos são ignorados."""

    assert _login(client).status_code == 200
    token = _csrf(client)
    data = client.put(
        "/api/settings",
        json={"settings": {"company.name": "Loja X", "secret_key": "hack", "x": 1}},
        headers={"X-CSRFToken": token},
    ).get_json()["settings"]

    assert data["company.name"] == "Loja X"
    assert "secret_key" not in data
    assert "x" not in data


def test_settings_put_rejects_non_dict(client):
    """PUT sem objeto settings devolve 400."""

    assert _login(client).status_code == 200
    token = _csrf(client)
    response = client.put(
        "/api/settings",
        json={"settings": ["nope"]},
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 400


def test_audit_lists_events(client):
    """GET /api/audit exige login e lista eventos registrados."""

    assert client.get("/api/audit").status_code == 401

    assert _login(client).status_code == 200
    token = _csrf(client)
    client.put(
        "/api/settings",
        json={"settings": {"company.name": "Loja X"}},
        headers={"X-CSRFToken": token},
    )
    events = client.get("/api/audit").get_json()["events"]

    assert any(
        e["action"] == "settings.update" and e["actor"] == "admin" for e in events
    )


def test_movement_validates(client):
    """POST /caixa/movement valida caixa aberto, tipo e valor."""

    assert _login(client).status_code == 200
    _close_caixa(client)
    token = _csrf(client)

    assert (
        client.post(
            "/api/caixa/movement",
            json={"kind": "sangria", "amount": "10.00"},
            headers={"X-CSRFToken": token},
        ).status_code
        == 400
    )

    _open_caixa(client)
    token = _csrf(client)
    for payload, status in (
        ({"kind": "retirada", "amount": "10.00"}, 400),
        ({"kind": "sangria", "amount": "0.00"}, 400),
        ({"kind": "sangria", "amount": "-5,00"}, 400),
        ({"kind": "sangria", "amount": "abc"}, 400),
    ):
        response = client.post(
            "/api/caixa/movement", json=payload, headers={"X-CSRFToken": token}
        )
        assert response.status_code == status, payload


def test_movement_affects_expected(client):
    """Sangria/suprimento entram no esperado: abertura + vendas + sup − sang."""

    assert _login(client).status_code == 200
    _close_caixa(client)
    _open_caixa(client, amount="100.00")
    token = _csrf(client)

    client.post(
        "/api/caixa/movement",
        json={"kind": "suprimento", "amount": "50.00", "obs": "troco"},
        headers={"X-CSRFToken": token},
    )
    client.post(
        "/api/caixa/movement",
        json={"kind": "sangria", "amount": "20.00"},
        headers={"X-CSRFToken": token},
    )

    payload = client.get("/api/caixa").get_json()
    assert payload["movement_totals"] == {"sangria": 20.0, "suprimento": 50.0}
    assert len(payload["movements"]) == 2
    assert payload["movements"][0]["kind"] == "sangria"

    close = client.post(
        "/api/caixa/close",
        json={"closing_details": {"1": "130.00"}},
        headers={"X-CSRFToken": _csrf(client)},
    )
    assert close.status_code == 200
    assert close.get_json()["last_closed"]["expected_amount"] == 130.0

    events = client.get("/api/audit?entity=cash_register").get_json()["events"]
    actions = {e["action"] for e in events}
    assert {"caixa.open", "caixa.sangria", "caixa.suprimento", "caixa.close"} <= actions


def test_cancel_records_audit(client):
    """Cancelar venda registra auditoria com motivo."""

    assert _login(client).status_code == 200
    token = _csrf(client)
    created = client.post(
        "/api/sales",
        json={"date": "2026-09-27", "total": "10,00"},
        headers={"X-CSRFToken": token},
    ).get_json()
    # A lista combinada vem ordenada por data; pega a venda AVULSA da data
    # certa (pedidos do PDV de hoje têm data mais nova e aparecem antes).
    sale_id = next(
        s["id"]
        for s in created["sales"]
        if s["kind"] == "manual" and s["date"] == "2026-09-27"
    )

    response = client.post(
        f"/api/sales/{sale_id}/cancel",
        json={"reason": "erro de lançamento"},
        headers={"X-CSRFToken": _csrf(client)},
    )
    assert response.status_code == 200

    events = client.get("/api/audit?entity=sale").get_json()["events"]
    cancel = next(e for e in events if e["action"] == "sale.cancel")
    assert cancel["entity_id"] == sale_id
    assert "erro de lançamento" in (cancel["details"] or "")
