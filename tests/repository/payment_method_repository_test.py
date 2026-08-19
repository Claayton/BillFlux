"""Tests for the PaymentMethodRepository Class"""

from billflux.infra.repository.payment_method_repository import PaymentMethodRepository


def _new_method():
    return PaymentMethodRepository().insert_method("Cartão Extra", sort_order=99)


def test_insert_and_get_method():
    """Inserting a payment method should persist it."""

    repository = PaymentMethodRepository()
    method = repository.insert_method("Dinheiro Teste")

    assert method.id is not None
    assert method.name == "Dinheiro Teste"
    assert method.active is True
    assert repository.get_method(method.id).name == "Dinheiro Teste"


def test_get_active_methods():
    """get_active_methods should return only active methods."""

    repository = PaymentMethodRepository()
    inactive = _new_method()
    repository.update_method(inactive.id, active=False)

    active = [method.id for method in repository.get_active_methods()]
    assert inactive.id not in active


def test_update_method():
    """Updating a method should change its fields."""

    repository = PaymentMethodRepository()
    method = _new_method()

    updated = repository.update_method(method.id, active=False)

    assert updated.active is False
    assert repository.get_method(method.id).active is False


def test_delete_method():
    """Deleting a method should remove it."""

    repository = PaymentMethodRepository()
    method = _new_method()

    assert repository.delete_method(method.id) is True
    assert repository.get_method(method.id) is None


def test_count_orders_zero_by_default():
    """A new method should have no linked orders."""

    repository = PaymentMethodRepository()
    method = _new_method()

    assert repository.count_orders(method.id) == 0
