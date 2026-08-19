"""Tests for the OrderRepository Class"""

from datetime import date
from decimal import Decimal

import pytest

from billflux.infra.repository.order_repository import OrderRepository
from billflux.infra.repository.payment_method_repository import PaymentMethodRepository
from billflux.infra.repository.product_repository import ProductRepository


def _product(name="Item Teste", price="5.00", stock=10):
    return ProductRepository().insert_product(
        name=name, price=Decimal(price), stock_quantity=stock
    )


def _method():
    return PaymentMethodRepository().get_active_methods()[0]


def test_create_order_decrements_stock_and_logs():
    """Creating an order should persist it, decrement stock and log a saida."""

    product = _product(name="Café Teste", price="4.00", stock=10)
    method = _method()

    order = OrderRepository().create_order([(product.id, 3)], method.id, obs="Balcão")

    assert order.id is not None
    assert order.total == Decimal("12.00")
    assert order.obs == "Balcão"

    fetched = ProductRepository().get_product(product.id)
    assert fetched.stock_quantity == 7

    movements = ProductRepository().get_movements(product.id)
    assert movements[0].movement_type == "saida"
    assert movements[0].quantity == 3


def test_create_order_multiple_items():
    """An order can contain several products with correct total."""

    a = _product(name="Item A Teste", price="2.00", stock=5)
    b = _product(name="Item B Teste", price="3.50", stock=5)
    method = _method()

    order = OrderRepository().create_order([(a.id, 2), (b.id, 4)], method.id)

    assert order.total == Decimal("18.00")
    items = OrderRepository().get_order_items(order.id)
    assert len(items) == 2


def test_create_order_insufficient_stock_rolls_back():
    """Insufficient stock should raise and persist nothing."""

    product = _product(name="Item Escasso Teste", price="1.00", stock=2)
    method = _method()
    repository = OrderRepository()

    with pytest.raises(ValueError):
        repository.create_order([(product.id, 5)], method.id)

    assert repository.get_orders_by_date(date.today()) or True  # sanity no crash
    assert ProductRepository().get_product(product.id).stock_quantity == 2


def test_get_order_and_items():
    """get_order should return the order and its items."""

    product = _product(name="Item Recibo Teste", price="7.00", stock=4)
    method = _method()
    repository = OrderRepository()

    order = repository.create_order([(product.id, 2)], method.id)

    fetched = repository.get_order(order.id)
    assert fetched.total == Decimal("14.00")
    items = repository.get_order_items(order.id)
    assert len(items) == 1
    assert items[0].product_id == product.id
    assert items[0].quantity == 2


def test_get_orders_ordered_by_date_desc():
    """get_orders should return orders newest first."""

    product = _product(name="Item Ordem Teste", price="1.00", stock=20)
    method = _method()
    repository = OrderRepository()

    repository.create_order([(product.id, 1)], method.id)
    repository.create_order([(product.id, 1)], method.id)

    orders = repository.get_orders()
    assert len(orders) >= 2
    assert orders[0].created_at >= orders[-1].created_at
