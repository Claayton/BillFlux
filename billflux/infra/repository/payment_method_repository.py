"""Module for repository to PaymentMethod (formas de pagamento)"""

from typing import List, Optional

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.payment_method import PaymentMethod as PaymentMethodModel
from billflux.domain.models.payment_methods import PaymentMethod


class PaymentMethodRepository:
    """PaymentMethod table data manipulation"""

    def insert_method(
        self, name: str, active: bool = True, sort_order: int = 0
    ) -> PaymentMethod:
        """Inserts a new payment method."""

        session = get_session()
        try:
            with session:
                method = PaymentMethodModel(
                    name=name, active=active, sort_order=sort_order
                )
                session.add(method)
                session.commit()
                session.refresh(method)
                return PaymentMethod(**dict(method))
        finally:
            session.close()

    def get_methods(self) -> List[PaymentMethod]:
        """Returns all payment methods ordered by sort order and id."""

        session = get_session()
        try:
            with session:
                sql = select(PaymentMethodModel).order_by(
                    PaymentMethodModel.sort_order, PaymentMethodModel.id
                )
                methods = session.exec(sql).all()
                return [PaymentMethod(**dict(method)) for method in methods]
        finally:
            session.close()

    def get_active_methods(self) -> List[PaymentMethod]:
        """Returns only active payment methods ordered by sort order."""

        session = get_session()
        try:
            with session:
                sql = (
                    select(PaymentMethodModel)
                    .where(PaymentMethodModel.active == True)  # noqa: E712
                    .order_by(PaymentMethodModel.sort_order, PaymentMethodModel.id)
                )
                methods = session.exec(sql).all()
                return [PaymentMethod(**dict(method)) for method in methods]
        finally:
            session.close()

    def get_method(self, method_id: int) -> Optional[PaymentMethod]:
        """Returns a payment method by its id."""

        session = get_session()
        try:
            with session:
                method = session.get(PaymentMethodModel, method_id)
                return PaymentMethod(**dict(method)) if method else None
        finally:
            session.close()

    def update_method(
        self, method_id: int, **fields: object
    ) -> Optional[PaymentMethod]:
        """Updates the fields of an existing payment method."""

        session = get_session()
        try:
            with session:
                method = session.get(PaymentMethodModel, method_id)
                if not method:
                    return None
                for key, value in fields.items():
                    setattr(method, key, value)
                session.add(method)
                session.commit()
                session.refresh(method)
                return PaymentMethod(**dict(method))
        finally:
            session.close()

    def delete_method(self, method_id: int) -> bool:
        """Deletes a payment method by its id."""

        session = get_session()
        try:
            with session:
                method = session.get(PaymentMethodModel, method_id)
                if not method:
                    return False
                session.delete(method)
                session.commit()
                return True
        finally:
            session.close()

    def count_orders(self, method_id: int) -> int:
        """Counts orders linked to a payment method."""

        from billflux.infra.entities.order import Order as OrderModel

        session = get_session()
        try:
            with session:
                sql = select(OrderModel).where(
                    OrderModel.payment_method_id == method_id
                )
                return len(session.exec(sql).all())
        finally:
            session.close()
