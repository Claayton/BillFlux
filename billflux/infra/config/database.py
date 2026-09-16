"""Module for database configuration and creation"""

# flake8: noqa: F405

from sqlalchemy import inspect, text
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine, Session
from billflux.config import settings
from billflux.infra.entities.bill import *  # pylint: disable=W0401, W0614
from billflux.infra.entities.account import Account  # noqa: F401
from billflux.infra.entities.sale import Sale  # noqa: F401
from billflux.infra.entities.product import Product  # noqa: F401
from billflux.infra.entities.product_movement import ProductMovement  # noqa: F401
from billflux.infra.entities.payment_method import PaymentMethod  # noqa: F401
from billflux.infra.entities.order import Order  # noqa: F401
from billflux.infra.entities.order_item import OrderItem  # noqa: F401
from billflux.infra.entities.order_payment import OrderPayment  # noqa: F401
from billflux.infra.entities.category import Category  # noqa: F401
from billflux.infra.entities.cash_register import CashRegister  # noqa: F401
from billflux.infra.entities.customer import Customer  # noqa: F401
from billflux.infra.entities.supplier import Supplier  # noqa: F401
from billflux.infra.entities.purchase_order import (
    PurchaseOrder as PurchaseOrderModel,
)  # noqa: F401
from billflux.infra.entities.purchase_item import (
    PurchaseItem as PurchaseItemModel,
)  # noqa: F401
from billflux.infra.entities.product_supplier import (
    ProductSupplier as ProductSupplierModel,
)  # noqa: F401
from billflux.infra.entities.product_unit import (
    ProductUnit as ProductUnitModel,
)  # noqa: F401

_database_url = settings.database.url

_engine_kwargs = {}
if _database_url.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    if ":memory:" in _database_url or _database_url == "sqlite://":
        _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(_database_url, **_engine_kwargs)

_is_sqlite = engine.dialect.name == "sqlite"


def _add_column_if_missing(table: str, column: str, column_type: str = "VARCHAR"):
    """Adds a column to an existing table without dropping data."""
    if not table.isidentifier() or not column.isidentifier():
        return
    with engine.connect() as connection:
        existing = [col["name"] for col in inspect(connection).get_columns(table)]
        if column not in existing:
            connection.execute(
                text(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
            )
            connection.commit()


def create_db():
    """Criando bancos de dados"""

    base = SQLModel.metadata.create_all(engine)
    if _is_sqlite:
        _add_column_if_missing("bill", "pix_key")
        _add_column_if_missing("bill", "pix_payload")
        _add_column_if_missing("bill", "pix_image")
        _add_column_if_missing("bill", "account_id", "INTEGER")
        _add_column_if_missing("orders", "cancelled", "BOOLEAN DEFAULT 0")
        _add_column_if_missing("orders", "discount", "NUMERIC(10,2)")
        _add_column_if_missing("sale", "cancelled", "BOOLEAN DEFAULT 0")
        _add_column_if_missing("product", "secondary_code", "VARCHAR")
        _add_column_if_missing("product", "category", "VARCHAR")
        _add_column_if_missing("product", "suppliers", "VARCHAR")
        _add_column_if_missing("product", "category_id", "INTEGER")
        _add_column_if_missing("cashregister", "opening_details", "VARCHAR")
        _add_column_if_missing("cashregister", "system_totals", "VARCHAR")
        _add_column_if_missing("cashregister", "closing_details", "VARCHAR")
        _add_column_if_missing("orders", "customer_id", "INTEGER")
        _add_column_if_missing("product", "supplier_id", "INTEGER")
        _add_column_if_missing("bill", "supplier_id", "INTEGER")
        _add_column_if_missing("purchase_item", "unit_com", "VARCHAR")
        _add_column_if_missing("product", "ideal_stock", "INTEGER DEFAULT 0")
        _add_column_if_missing(
            "productsupplier", "frequency", "VARCHAR DEFAULT 'semanal'"
        )
        _add_column_if_missing("productsupplier", "week_parity", "INTEGER DEFAULT 0")

        _migrate_category_text()
        _migrate_product_units()

    return base


def _migrate_category_text():
    """Converte o texto de categoria dos produtos em registros de categoria."""
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT id, category FROM product "
                "WHERE category_id IS NULL AND category IS NOT NULL AND category != ''"
            )
        ).fetchall()
        if not rows:
            return
        for product_id, name in rows:
            existing = connection.execute(
                text("SELECT id FROM category WHERE name = :name"), {"name": name}
            ).fetchone()
            if existing:
                category_id = existing[0]
            else:
                result = connection.execute(
                    text("INSERT INTO category (name, active) VALUES (:name, 1)"),
                    {"name": name},
                )
                category_id = result.lastrowid
            connection.execute(
                text("UPDATE product SET category_id = :cid WHERE id = :pid"),
                {"cid": category_id, "pid": product_id},
            )
        connection.commit()


def _migrate_product_units():
    """Cria apresentação padrão 'Unidade' para produtos que não possuem nenhuma."""
    with engine.connect() as connection:
        existing = connection.execute(
            text("SELECT COUNT(*) FROM product_unit")
        ).fetchone()[0]
        if existing > 0:
            return
        rows = connection.execute(
            text("SELECT id, price FROM product WHERE active = 1")
        ).fetchall()
        if not rows:
            return
        for product_id, price in rows:
            connection.execute(
                text(
                    "INSERT INTO product_unit (product_id, name, barcode, factor, price, is_default) "
                    "VALUES (:pid, 'Unidade', NULL, 1, :price, 1)"
                ),
                {"pid": product_id, "price": float(price or 0)},
            )
        connection.commit()


def get_session():
    """GetSession from database function"""
    return Session(engine)
