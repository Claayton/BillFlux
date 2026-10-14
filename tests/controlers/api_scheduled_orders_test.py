"""Tests for scheduled orders (agenda de pedidos a clientes)."""

from decimal import Decimal


def _csrf(client):
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    return response.get_json()["csrf_token"]


def _customer(name="João da Silva"):
    from billflux.infra.repository.customer_repository import CustomerRepository

    return CustomerRepository().insert_customer(name=name, active=True)


def test_scheduled_orders_require_login(client):
    assert client.get("/api/scheduled-orders").status_code == 401


def test_create_and_list_scheduled_order(logged_client):
    token = _csrf(logged_client)
    customer = _customer()

    resp = logged_client.post(
        "/api/scheduled-orders",
        json={
            "customer_id": customer.id,
            "order_date": "2026-11-20",
            "order_time": "10:30",
            "status": "pendente",
            "obs": "Entregar na loja",
            "items": [
                {
                    "product_id": 1,
                    "name": "Gelo 5kg",
                    "quantity": 2,
                    "unit_price": "30,00",
                },
                {"name": "Gelo 2kg", "quantity": 1, "unit_price": "15,00"},
            ],
        },
        headers={"X-CSRFToken": token},
    )
    assert resp.status_code == 201, resp.get_json()
    order = resp.get_json()["order"]
    assert order["customer_name"] == "João da Silva"
    assert order["status"] == "pendente"
    assert Decimal(order["total"]) == Decimal("75")  # 2×30 + 1×15
    assert len(order["items"]) == 2
    assert order["items"][0]["name"] == "Gelo 5kg"

    listing = logged_client.get("/api/scheduled-orders?date=2026-11-20").get_json()[
        "orders"
    ]
    assert any(o["id"] == order["id"] for o in listing)


def test_create_scheduled_order_free_customer_name(logged_client):
    token = _csrf(logged_client)
    resp = logged_client.post(
        "/api/scheduled-orders",
        json={"customer_name": "Cliente avulso", "order_date": "2026-11-21"},
        headers={"X-CSRFToken": token},
    )
    assert resp.status_code == 201
    assert resp.get_json()["order"]["customer_name"] == "Cliente avulso"


def test_create_scheduled_order_requires_customer(logged_client):
    token = _csrf(logged_client)
    resp = logged_client.post(
        "/api/scheduled-orders",
        json={"order_date": "2026-11-21"},
        headers={"X-CSRFToken": token},
    )
    assert resp.status_code == 400


def test_update_status_and_delete(logged_client):
    token = _csrf(logged_client)
    created = logged_client.post(
        "/api/scheduled-orders",
        json={"customer_name": "Zed", "order_date": "2026-11-22"},
        headers={"X-CSRFToken": token},
    ).get_json()["order"]

    changed = logged_client.post(
        f"/api/scheduled-orders/{created['id']}/status",
        json={"status": "entregado"},
        headers={"X-CSRFToken": token},
    )
    assert changed.status_code == 200
    assert changed.get_json()["order"]["status"] == "entregado"

    invalid = logged_client.post(
        f"/api/scheduled-orders/{created['id']}/status",
        json={"status": "xyz"},
        headers={"X-CSRFToken": token},
    )
    assert invalid.status_code == 400

    deleted = logged_client.delete(
        f"/api/scheduled-orders/{created['id']}", headers={"X-CSRFToken": token}
    )
    assert deleted.status_code == 200
    assert (
        logged_client.get(f"/api/scheduled-orders/{created['id']}").status_code == 404
    )


def test_update_scheduled_order_replaces_items(logged_client):
    token = _csrf(logged_client)
    created = logged_client.post(
        "/api/scheduled-orders",
        json={
            "customer_name": "Maria",
            "order_date": "2026-11-23",
            "items": [{"name": "Gelo", "quantity": 1, "unit_price": "10"}],
        },
        headers={"X-CSRFToken": token},
    ).get_json()["order"]
    assert Decimal(created["total"]) == Decimal("10")

    updated = logged_client.put(
        f"/api/scheduled-orders/{created['id']}",
        json={
            "customer_name": "Maria",
            "order_date": "2026-11-24",
            "items": [{"name": "Gelo", "quantity": 3, "unit_price": "10"}],
        },
        headers={"X-CSRFToken": token},
    )
    assert updated.status_code == 200
    order = updated.get_json()["order"]
    assert order["order_date"] == "2026-11-24"
    assert Decimal(order["total"]) == Decimal("30")
