"""Tests for the ProductRepository Class"""

from decimal import Decimal

from billflux.infra.repository.product_repository import ProductRepository


def test_insert_and_get_product():
    """Inserting a product should persist it and return its data."""

    repository = ProductRepository()
    product = repository.insert_product(
        name="Coca-Cola 2L",
        price=Decimal("8.50"),
        barcode="7891000112345",
        stock_quantity=10,
        min_stock=2,
        obs="Fornecedor A",
    )

    assert product.id is not None
    assert product.name == "Coca-Cola 2L"
    assert product.price == Decimal("8.50")
    assert product.barcode == "7891000112345"
    assert product.stock_quantity == 10

    fetched = repository.get_product(product.id)
    assert fetched.name == "Coca-Cola 2L"
    assert repository.get_product_by_barcode("7891000112345").id == product.id


def test_insert_product_logs_initial_stock():
    """Products created with stock should log an entrada movement."""

    repository = ProductRepository()
    product = repository.insert_product(
        name="Água 500ml", price=Decimal("2.00"), stock_quantity=24
    )

    movements = repository.get_movements(product.id)
    assert len(movements) == 1
    assert movements[0].movement_type == "entrada"
    assert movements[0].quantity == 24


def test_update_product():
    """Updating a product should change its fields."""

    repository = ProductRepository()
    product = repository.insert_product(name="Pão", price=Decimal("1.50"))

    updated = repository.update_product(product.id, price=Decimal("2.00"), active=False)

    assert updated.price == Decimal("2.00")
    assert updated.active is False
    assert repository.get_product(product.id).price == Decimal("2.00")


def test_adjust_stock_increases():
    """A positive adjustment should increase stock and log a movement."""

    repository = ProductRepository()
    product = repository.insert_product(name="Salgadinho", price=Decimal("3.00"))

    updated = repository.adjust_stock(
        product.id, 5, obs="Entrada de mercadoria", movement_type="ajuste"
    )

    assert updated.stock_quantity == 5
    movements = repository.get_movements(product.id)
    assert movements[0].movement_type == "ajuste"
    assert movements[0].quantity == 5


def test_adjust_stock_negative():
    """A negative adjustment should decrease stock."""

    repository = ProductRepository()
    product = repository.insert_product(
        name="Chocolate", price=Decimal("4.00"), stock_quantity=8
    )

    updated = repository.adjust_stock(product.id, -3, obs="Quebra")

    assert updated.stock_quantity == 5
    movements = repository.get_movements(product.id)
    assert movements[0].movement_type == "ajuste"
    assert movements[0].quantity == -3


def test_adjust_stock_does_not_go_below_zero():
    """Stock should never become negative."""

    repository = ProductRepository()
    product = repository.insert_product(
        name="Bala", price=Decimal("0.50"), stock_quantity=2
    )

    result = repository.adjust_stock(product.id, -5)

    assert result is None
    assert repository.get_product(product.id).stock_quantity == 2


def test_get_active_products():
    """get_active_products should return only active ones."""

    repository = ProductRepository()
    repository.insert_product(name="Ativo Teste", price=Decimal("1.00"))
    inactive = repository.insert_product(name="Inativo Teste", price=Decimal("1.00"))
    repository.update_product(inactive.id, active=False)

    names = [product.name for product in repository.get_active_products()]
    assert "Ativo Teste" in names
    assert "Inativo Teste" not in names


def test_delete_product():
    """Deleting a product should remove it."""

    repository = ProductRepository()
    product = repository.insert_product(name="Temp Delete", price=Decimal("1.00"))

    assert repository.delete_product(product.id) is True
    assert repository.get_product(product.id) is None


def test_count_orders_zero_by_default():
    """A new product should have no linked orders."""

    repository = ProductRepository()
    product = repository.insert_product(name="Sem Vendas", price=Decimal("1.00"))

    assert repository.count_orders(product.id) == 0
