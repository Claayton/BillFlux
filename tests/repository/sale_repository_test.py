"""Tests for the SaleRepository Class"""

from datetime import date
from decimal import Decimal

from billflux.infra.repository.sale_repository import SaleRepository


def test_insert_sale():
    """Inserting a daily sale should persist it and return its data."""

    repository = SaleRepository()
    sale = repository.insert_sale(date(2026, 1, 5), Decimal("1234.50"), "Feira")

    assert sale.id is not None
    assert sale.date == date(2026, 1, 5)
    assert sale.total == Decimal("1234.50")
    assert sale.obs == "Feira"

    fetched = repository.get_sale_by_date(date(2026, 1, 5))
    assert fetched.total == Decimal("1234.50")


def test_upsert_same_date_updates():
    """Launching again on the same date should update, not duplicate."""

    repository = SaleRepository()
    first = repository.insert_sale(date(2026, 2, 10), Decimal("500.00"))
    second = repository.insert_sale(date(2026, 2, 10), Decimal("800.00"), "Noite")

    assert second.id == first.id
    assert repository.get_sale_by_date(date(2026, 2, 10)).total == Decimal("800.00")
    assert repository.get_sale_by_date(date(2026, 2, 10)).obs == "Noite"


def test_delete_sale():
    """Deleting a daily sale should remove it."""

    repository = SaleRepository()
    sale = repository.insert_sale(date(2026, 3, 1), Decimal("300.00"))

    assert repository.delete_sale(sale.id) is True
    assert repository.get_sale(sale.id) is None


def test_get_sales_ordered_by_date_desc():
    """get_sales should return sales ordered from newest to oldest."""

    repository = SaleRepository()
    repository.insert_sale(date(2026, 1, 1), Decimal("10.00"))
    repository.insert_sale(date(2026, 1, 2), Decimal("20.00"))

    sales = repository.get_sales()
    assert sales[0].date >= sales[-1].date
