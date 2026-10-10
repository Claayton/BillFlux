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


def test_products_create_with_details(logged_client):
    """POST cadastra produto com categoria, código secundário e fornecedores."""

    token = _csrf(logged_client)

    cat_resp = logged_client.post(
        "/api/categories",
        json={"name": "Bebidas"},
        headers={"X-CSRFToken": token},
    )
    cat_id = next(
        c["id"] for c in cat_resp.get_json()["categories"] if c["name"] == "Bebidas"
    )

    response = logged_client.post(
        "/api/products",
        json={
            "name": "Com detalhes",
            "price": "12,50",
            "cost": "6,00",
            "barcode": "7900000000100",
            "secondary_code": "SEC-007",
            "category_id": cat_id,
            "suppliers": "Distribuidora ABC, Atacadão",
            "min_stock": 3,
        },
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 201
    product = next(
        p for p in response.get_json()["products"] if p["name"] == "Com detalhes"
    )
    assert product["secondary_code"] == "SEC-007"
    assert product["category_id"] == cat_id
    assert product["category_name"] == "Bebidas"
    assert product["suppliers"] == "Distribuidora ABC, Atacadão"
    assert product["min_stock"] == 3


def test_products_edit_details(logged_client):
    """PUT atualiza os campos de detalhe do produto."""

    token = _csrf(logged_client)

    cat_resp = logged_client.post(
        "/api/categories",
        json={"name": "Padaria"},
        headers={"X-CSRFToken": token},
    )
    cat_id = next(
        c["id"] for c in cat_resp.get_json()["categories"] if c["name"] == "Padaria"
    )

    created = logged_client.post(
        "/api/products",
        json={"name": "Detalhe", "price": "1,00"},
        headers={"X-CSRFToken": token},
    ).get_json()
    product_id = next(p["id"] for p in created["products"] if p["name"] == "Detalhe")

    response = logged_client.put(
        f"/api/products/{product_id}",
        json={
            "name": "Detalhe",
            "price": "1,00",
            "cost": "0,50",
            "category_id": cat_id,
            "secondary_code": "SEC-999",
            "suppliers": "Fornecedor X",
        },
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 200
    product = next(p for p in response.get_json()["products"] if p["id"] == product_id)
    assert product["category_id"] == cat_id
    assert product["category_name"] == "Padaria"
    assert product["secondary_code"] == "SEC-999"
    assert product["suppliers"] == "Fornecedor X"


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


def test_products_edit_syncs_default_unit_price(logged_client):
    """PUT com preço novo espelha na apresentação padrão (PDV usa ela)."""

    token = _csrf(logged_client)
    created = logged_client.post(
        "/api/products",
        json={"name": "Sinc", "price": "10,00"},
        headers={"X-CSRFToken": token},
    ).get_json()
    product_id = next(p["id"] for p in created["products"] if p["name"] == "Sinc")

    logged_client.post(
        f"/api/products/{product_id}/units",
        json={"name": "Unidade", "factor": 1, "price": "10,00", "is_default": True},
        headers={"X-CSRFToken": token},
    )
    logged_client.post(
        f"/api/products/{product_id}/units",
        json={"name": "Caixa", "factor": 12, "price": "100,00"},
        headers={"X-CSRFToken": token},
    )

    response = logged_client.put(
        f"/api/products/{product_id}",
        json={"name": "Sinc", "price": "12,00", "cost": "5,00"},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200

    units = logged_client.get(f"/api/products/{product_id}/units").get_json()["units"]
    by_name = {u["name"]: u for u in units}
    assert by_name["Unidade"]["price"] == 12.0
    assert by_name["Caixa"]["price"] == 100.0


def _product_id_by_name(client, name):
    products = client.get("/api/products").get_json()["products"]
    return next(p["id"] for p in products if p["name"] == name)


def test_create_default_unit_sets_product_price(logged_client):
    """Cadastrar a 'Unidade' (default, fator 1) define o preço-base do produto."""
    token = _csrf(logged_client)
    logged_client.post(
        "/api/products",
        json={"name": "Heineken New", "price": "0,00"},
        headers={"X-CSRFToken": token},
    )
    product_id = _product_id_by_name(logged_client, "Heineken New")

    logged_client.post(
        f"/api/products/{product_id}/units",
        json={"name": "Unidade", "factor": 1, "price": "9,99", "is_default": True},
        headers={"X-CSRFToken": token},
    )
    logged_client.post(
        f"/api/products/{product_id}/units",
        json={"name": "Pack c/ 6", "factor": 6, "price": "47,99"},
        headers={"X-CSRFToken": token},
    )

    products = logged_client.get("/api/products").get_json()["products"]
    product = next(p for p in products if p["id"] == product_id)
    assert product["price"] == 9.99  # Unidade define o preço-base, NÃO o pack

    units = logged_client.get(f"/api/products/{product_id}/units").get_json()["units"]
    units_by_name = {u["name"]: u for u in units}
    assert units_by_name["Unidade"]["price"] == 9.99
    assert units_by_name["Pack c/ 6"]["price"] == 47.99


def test_update_default_unit_syncs_product_price(logged_client):
    """Editar o preço da 'Unidade' padrão acompanha o preço-base do produto."""
    token = _csrf(logged_client)
    logged_client.post(
        "/api/products",
        json={"name": "Sinc Reverse", "price": "0,00"},
        headers={"X-CSRFToken": token},
    )
    product_id = _product_id_by_name(logged_client, "Sinc Reverse")
    unit_id = logged_client.post(
        f"/api/products/{product_id}/units",
        json={"name": "Unidade", "factor": 1, "price": "9,99", "is_default": True},
        headers={"X-CSRFToken": token},
    ).get_json()["unit"]["id"]

    logged_client.put(
        f"/api/product-units/{unit_id}",
        json={
            "product_id": product_id,
            "name": "Unidade",
            "factor": 1,
            "price": "8,50",
        },
        headers={"X-CSRFToken": token},
    )

    products = logged_client.get("/api/products").get_json()["products"]
    product = next(p for p in products if p["id"] == product_id)
    assert product["price"] == 8.5


def test_pack_cannot_be_default(logged_client):
    """Apresentação com fator > 1 não pode ser a padrão."""
    token = _csrf(logged_client)
    logged_client.post(
        "/api/products",
        json={"name": "Pack Default", "price": "10,00"},
        headers={"X-CSRFToken": token},
    )
    product_id = _product_id_by_name(logged_client, "Pack Default")

    resp = logged_client.post(
        f"/api/products/{product_id}/units",
        json={"name": "Pack c/ 6", "factor": 6, "price": "47,99", "is_default": True},
        headers={"X-CSRFToken": token},
    )
    assert resp.status_code == 400


def test_delete_product_removes_presentation(logged_client):
    """DELETE remove o produto e a apresentação própria (product_unit)."""

    from decimal import Decimal

    from billflux.infra.repository.product_repository import ProductRepository
    from billflux.infra.repository.product_unit_repository import (
        ProductUnitRepository,
    )

    token = _csrf(logged_client)
    product = ProductRepository().insert_product(
        name="Com apresentação", price=Decimal("5.00"), stock_quantity=10
    )
    ProductUnitRepository().upsert(
        product_id=product.id,
        name="Unidade",
        factor=1,
        price=Decimal("5.00"),
        is_default=True,
    )

    response = logged_client.delete(
        f"/api/products/{product.id}", headers={"X-CSRFToken": token}
    )

    assert response.status_code == 200
    assert ProductRepository().get_product(product.id) is None
    assert ProductUnitRepository().get_units_for_product(product.id) == []


def test_delete_product_blocked_by_sale(logged_client):
    """Produto vendido não é excluído: 400 com motivo (não mais 500)."""

    from decimal import Decimal

    from billflux.infra.repository.order_repository import OrderRepository
    from billflux.infra.repository.payment_method_repository import (
        PaymentMethodRepository,
    )
    from billflux.infra.repository.product_repository import ProductRepository

    token = _csrf(logged_client)
    product = ProductRepository().insert_product(
        name="Vendido", price=Decimal("5.00"), stock_quantity=10
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    OrderRepository().create_order([(product.id, 1)], method.id)

    response = logged_client.delete(
        f"/api/products/{product.id}", headers={"X-CSRFToken": token}
    )

    assert response.status_code == 400
    assert "vendido" in response.get_json()["error"]
    assert ProductRepository().get_product(product.id) is not None


def test_delete_product_blocked_by_movement(logged_client):
    """Produto com movimentação de estoque não é excluído (400)."""

    from decimal import Decimal

    from billflux.infra.repository.product_repository import ProductRepository

    token = _csrf(logged_client)
    product = ProductRepository().insert_product(
        name="Com movimento", price=Decimal("5.00"), stock_quantity=10
    )
    ProductRepository().adjust_stock(product.id, 1, obs="ajuste")

    response = logged_client.delete(
        f"/api/products/{product.id}", headers={"X-CSRFToken": token}
    )

    assert response.status_code == 400
    assert "movimenta" in response.get_json()["error"]


def test_toggle_product_active(logged_client):
    """POST /toggle alterna o active do produto."""

    from decimal import Decimal

    from billflux.infra.repository.product_repository import ProductRepository

    token = _csrf(logged_client)
    product = ProductRepository().insert_product(
        name="Liga e desliga", price=Decimal("5.00"), stock_quantity=1
    )

    first = logged_client.post(
        f"/api/products/{product.id}/toggle", headers={"X-CSRFToken": token}
    )
    assert first.status_code == 200
    assert ProductRepository().get_product(product.id).active is False

    second = logged_client.post(
        f"/api/products/{product.id}/toggle", headers={"X-CSRFToken": token}
    )
    assert second.status_code == 200
    assert ProductRepository().get_product(product.id).active is True


def test_delete_missing_product(logged_client):
    """DELETE de produto inexistente devolve 404."""

    token = _csrf(logged_client)
    response = logged_client.delete(
        "/api/products/999999", headers={"X-CSRFToken": token}
    )
    assert response.status_code == 404
