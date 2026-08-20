"""Tests for the products JSON API (SPA)."""


def _csrf(client):
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    return response.get_json()["csrf_token"]


def test_products_requires_login(client):
    """Sem sessão, /api/products deve devolver 401 JSON."""

    assert client.get("/api/products").status_code == 401


def test_products_list(logged_client):
    """Lista o catálogo de produtos."""

    response = logged_client.get("/api/products")

    assert response.status_code == 200
    assert isinstance(response.get_json()["products"], list)


def test_products_create(logged_client):
    """POST cadastra um produto com preço e estoque."""

    token = _csrf(logged_client)
    response = logged_client.post(
        "/api/products",
        json={
            "name": "Refrigerante 2L",
            "price": "9,90",
            "cost": "5,00",
            "stock_quantity": 10,
            "min_stock": 2,
            "barcode": "7900000000001",
        },
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 201
    product = next(
        p for p in response.get_json()["products"] if p["name"] == "Refrigerante 2L"
    )
    assert product["price"] == 9.9
    assert product["cost"] == 5.0
    assert product["stock_quantity"] == 10


def test_products_create_duplicate_barcode(logged_client):
    """POST com código de barras repetido deve devolver 400."""

    token = _csrf(logged_client)
    logged_client.post(
        "/api/products",
        json={"name": "Coca 2L", "price": "9,90", "barcode": "7900000000002"},
        headers={"X-CSRFToken": token},
    )
    dup = logged_client.post(
        "/api/products",
        json={"name": "Coca 3L", "price": "9,90", "barcode": "7900000000002"},
        headers={"X-CSRFToken": token},
    )
    assert dup.status_code == 400


def test_products_create_validation(logged_client):
    """POST sem nome ou com preço inválido deve devolver 400."""

    token = _csrf(logged_client)
    missing = logged_client.post(
        "/api/products",
        json={"name": "", "price": "1,00"},
        headers={"X-CSRFToken": token},
    )
    assert missing.status_code == 400

    invalid = logged_client.post(
        "/api/products",
        json={"name": "X", "price": "abc"},
        headers={"X-CSRFToken": token},
    )
    assert invalid.status_code == 400


def test_products_edit(logged_client):
    """PUT atualiza nome, preço e status."""

    token = _csrf(logged_client)
    created = logged_client.post(
        "/api/products",
        json={"name": "Antes", "price": "1,00"},
        headers={"X-CSRFToken": token},
    ).get_json()
    product_id = next(p["id"] for p in created["products"] if p["name"] == "Antes")

    response = logged_client.put(
        f"/api/products/{product_id}",
        json={"name": "Depois", "price": "2,50", "cost": "1,00", "active": False},
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 200
    product = next(p for p in response.get_json()["products"] if p["id"] == product_id)
    assert product["name"] == "Depois"
    assert product["price"] == 2.5
    assert product["active"] is False


def test_products_adjust_stock(logged_client):
    """POST /adjust altera o estoque e registra movimento."""

    token = _csrf(logged_client)
    created = logged_client.post(
        "/api/products",
        json={"name": "Estoque", "price": "1,00", "stock_quantity": 5},
        headers={"X-CSRFToken": token},
    ).get_json()
    product_id = next(p["id"] for p in created["products"] if p["name"] == "Estoque")

    response = logged_client.post(
        f"/api/products/{product_id}/adjust",
        json={"delta": 3, "obs": "Entrada"},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200
    product = next(p for p in response.get_json()["products"] if p["id"] == product_id)
    assert product["stock_quantity"] == 8

    movements = logged_client.get(f"/api/products/{product_id}/movements")
    assert movements.status_code == 200
    assert len(movements.get_json()["movements"]) == 2  # inicial + ajuste


def test_products_delete(logged_client):
    """DELETE remove um produto sem vendas."""

    token = _csrf(logged_client)
    created = logged_client.post(
        "/api/products",
        json={"name": "Remover", "price": "1,00"},
        headers={"X-CSRFToken": token},
    ).get_json()
    product_id = next(p["id"] for p in created["products"] if p["name"] == "Remover")

    response = logged_client.delete(
        f"/api/products/{product_id}", headers={"X-CSRFToken": token}
    )
    assert response.status_code == 200
    assert not any(p["id"] == product_id for p in response.get_json()["products"])

    missing = logged_client.delete(
        "/api/products/999999", headers={"X-CSRFToken": token}
    )
    assert missing.status_code == 404
