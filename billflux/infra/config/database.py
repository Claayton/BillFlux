"""Module for database configuration and creation"""

# flake8: noqa: F405

from sqlalchemy import event
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
from billflux.infra.entities.cash_movement import CashMovement  # noqa: F401
from billflux.infra.entities.audit_event import AuditEvent  # noqa: F401
from billflux.infra.entities.setting import Setting  # noqa: F401
from billflux.infra.entities.receivable import Receivable  # noqa: F401
from billflux.infra.entities.receivable_payment import (  # noqa: F401
    ReceivablePayment,
)
from billflux.infra.entities.tab import Tab  # noqa: F401
from billflux.infra.entities.tab_item import TabItem  # noqa: F401

_database_url = settings.database.url

_engine_kwargs = {}
if _database_url.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    if ":memory:" in _database_url or _database_url == "sqlite://":
        _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(_database_url, **_engine_kwargs)

_is_sqlite = engine.dialect.name == "sqlite"

if _is_sqlite:
    # O SQLite não aplica FKs por padrão. Ativar garante que dev/testes
    # peguem violações de chave estrangeira (como acontece no Postgres).
    @event.listens_for(engine, "connect")
    def _sqlite_enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_db():
    """Cria o schema a partir dos models.

    Usado por testes e bootstrap; em dev/produção o schema é gerenciado pelo
    Alembic (``alembic upgrade head``)."""

    return SQLModel.metadata.create_all(engine)


def get_session():
    """GetSession from database function"""
    return Session(engine)
