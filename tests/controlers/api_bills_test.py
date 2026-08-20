"""Tests for the bills JSON API (SPA)."""


def _csrf(client):
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    return response.get_json()["csrf_token"]


def test_bills_requires_login(client):
    """Sem sessão, /api/bills deve devolver 401 JSON."""

    assert client.get("/api/bills").status_code == 401


def test_bills_list(logged_client):
    """Lista devolve stats, categorias e contas."""

    response = logged_client.get("/api/bills")

    assert response.status_code == 200
    data = response.get_json()
    assert set(data["stats"]) == {"open", "overdue", "paid_month", "total"}
    assert isinstance(data["account_groups"], list)
    assert isinstance(data["bills"], list)


def test_bills_create_and_status(logged_client):
    """POST cadastra uma conta e ela aparece como vencida quando passou."""

    token = _csrf(logged_client)
    response = logged_client.post(
        "/api/bills",
        json={
            "value": "250,90",
            "due_date": "2020-01-10",
            "reference": "Energia",
            "suplyer": "CEMIG",
            "obs": "Teste",
        },
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 201
    data = response.get_json()
    bill = next(b for b in data["bills"] if b["reference"] == "Energia")
    assert bill["value"] == 250.9
    assert bill["status"] == "vencida"
    assert bill["suplyer"] == "CEMIG"


def test_bills_create_validation(logged_client):
    """POST sem valor ou vencimento deve devolver 400."""

    token = _csrf(logged_client)
    missing = logged_client.post("/api/bills", json={}, headers={"X-CSRFToken": token})
    assert missing.status_code == 400


def test_bills_edit(logged_client):
    """PUT atualiza os campos de uma conta."""

    token = _csrf(logged_client)
    created = logged_client.post(
        "/api/bills",
        json={"value": "100,00", "due_date": "2026-12-01", "reference": "Ajuste"},
        headers={"X-CSRFToken": token},
    ).get_json()
    bill_id = next(b["id"] for b in created["bills"] if b["reference"] == "Ajuste")

    response = logged_client.put(
        f"/api/bills/{bill_id}",
        json={"value": "120,00", "due_date": "2026-12-15", "suplyer": "Novo"},
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 200
    bill = next(b for b in response.get_json()["bills"] if b["id"] == bill_id)
    assert bill["value"] == 120.0
    assert bill["suplyer"] == "Novo"


def test_bills_pay(logged_client):
    """POST /pay marca a conta como paga."""

    token = _csrf(logged_client)
    created = logged_client.post(
        "/api/bills",
        json={"value": "50,00", "due_date": "2026-12-01", "reference": "Pagar"},
        headers={"X-CSRFToken": token},
    ).get_json()
    bill_id = next(b["id"] for b in created["bills"] if b["reference"] == "Pagar")

    response = logged_client.post(
        f"/api/bills/{bill_id}/pay", headers={"X-CSRFToken": token}
    )

    assert response.status_code == 200
    bill = next(b for b in response.get_json()["bills"] if b["id"] == bill_id)
    assert bill["status"] == "paga"


def test_bills_create_paid(logged_client):
    """POST com status=true já cadastra a conta como paga."""

    token = _csrf(logged_client)
    response = logged_client.post(
        "/api/bills",
        json={
            "value": "90,00",
            "due_date": "2026-12-01",
            "reference": "Paga na criação",
            "status": True,
        },
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 201
    bill = next(
        b for b in response.get_json()["bills"] if b["reference"] == "Paga na criação"
    )
    assert bill["status"] == "paga"
    assert bill["payday"] is not None


def test_bills_unmark_paid(logged_client):
    """PUT com status=false desmarca uma conta paga."""

    token = _csrf(logged_client)
    created = logged_client.post(
        "/api/bills",
        json={"value": "40,00", "due_date": "2026-12-01", "reference": "Desmarcar"},
        headers={"X-CSRFToken": token},
    ).get_json()
    bill_id = next(b["id"] for b in created["bills"] if b["reference"] == "Desmarcar")
    logged_client.post(f"/api/bills/{bill_id}/pay", headers={"X-CSRFToken": token})

    response = logged_client.put(
        f"/api/bills/{bill_id}",
        json={
            "value": "40,00",
            "due_date": "2026-12-01",
            "reference": "Desmarcar",
            "status": False,
        },
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 200
    bill = next(b for b in response.get_json()["bills"] if b["id"] == bill_id)
    assert bill["status"] == "pendente"
    assert bill["payday"] is None


def test_bills_delete(logged_client):
    """DELETE remove uma conta."""

    token = _csrf(logged_client)
    created = logged_client.post(
        "/api/bills",
        json={"value": "30,00", "due_date": "2026-12-01", "reference": "Apagar"},
        headers={"X-CSRFToken": token},
    ).get_json()
    bill_id = next(b["id"] for b in created["bills"] if b["reference"] == "Apagar")

    response = logged_client.delete(
        f"/api/bills/{bill_id}", headers={"X-CSRFToken": token}
    )

    assert response.status_code == 200
    assert not any(b["id"] == bill_id for b in response.get_json()["bills"])

    missing = logged_client.delete("/api/bills/999999", headers={"X-CSRFToken": token})
    assert missing.status_code == 404
