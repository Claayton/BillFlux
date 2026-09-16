"""Module for repository to CashRegister (controle de caixa)"""

import json
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.cash_register import CashRegister as CashRegisterModel
from billflux.infra.entities.order import Order as OrderModel
from billflux.infra.entities.order_payment import OrderPayment as OrderPaymentModel
from billflux.domain.models.cash_registers import CashRegister


def _to_domain(cr: CashRegisterModel) -> CashRegister:
    return CashRegister(**dict(cr))


def _to_domains(items: List[CashRegisterModel]) -> List[CashRegister]:
    return [_to_domain(item) for item in items]


class CashRegisterRepository:
    """CashRegister table data manipulation"""

    def get_open(self) -> Optional[CashRegister]:
        """Returns the currently open register, if any."""

        session = get_session()
        try:
            with session:
                sql = select(CashRegisterModel).where(
                    CashRegisterModel.status == "open"
                )
                cr = session.exec(sql).first()
                return _to_domain(cr) if cr else None
        finally:
            session.close()

    def get_last_closed(self) -> Optional[CashRegister]:
        """Returns the last closed register."""

        session = get_session()
        try:
            with session:
                sql = (
                    select(CashRegisterModel)
                    .where(CashRegisterModel.status == "closed")
                    .order_by(CashRegisterModel.closed_at.desc())
                )
                cr = session.exec(sql).first()
                return _to_domain(cr) if cr else None
        finally:
            session.close()

    def get_history(self, limit: int = 20) -> List[CashRegister]:
        """Returns recent registers (open + closed)."""

        session = get_session()
        try:
            with session:
                sql = (
                    select(CashRegisterModel)
                    .order_by(CashRegisterModel.id.desc())
                    .limit(limit)
                )
                return _to_domains(session.exec(sql).all())
        finally:
            session.close()

    def open_register(
        self,
        opened_by: str,
        opened_at: str,
        opening_amount: float,
        opening_details: Optional[str] = None,
    ) -> CashRegister:
        """Opens a new register session."""

        session = get_session()
        try:
            with session:
                cr = CashRegisterModel(
                    opened_by=opened_by,
                    opened_at=opened_at,
                    opening_amount=opening_amount,
                    status="open",
                    opening_details=opening_details,
                )
                session.add(cr)
                session.commit()
                session.refresh(cr)
                return _to_domain(cr)
        finally:
            session.close()

    def close_register(
        self,
        register_id: int,
        closed_by: str,
        closed_at: str,
        closing_amount: float,
        expected_amount: float,
        obs: Optional[str] = None,
        system_totals: Optional[str] = None,
        closing_details: Optional[str] = None,
    ) -> Optional[CashRegister]:
        """Closes an open register session."""

        session = get_session()
        try:
            with session:
                cr = session.get(CashRegisterModel, register_id)
                if not cr or cr.status != "open":
                    return None
                cr.closed_by = closed_by
                cr.closed_at = closed_at
                cr.closing_amount = closing_amount
                cr.expected_amount = expected_amount
                cr.status = "closed"
                cr.obs = obs
                cr.system_totals = system_totals
                cr.closing_details = closing_details
                session.add(cr)
                session.commit()
                session.refresh(cr)
                return _to_domain(cr)
        finally:
            session.close()

    def compute_system_totals(self, opened_at: str, closed_at: str) -> Dict[str, float]:
        """Soma os valores por forma de pagamento entre opened_at e closed_at."""

        def _parse(value):
            if isinstance(value, datetime):
                return value
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

        opened = _parse(opened_at)
        closed = _parse(closed_at)

        session = get_session()
        try:
            with session:
                rows = session.execute(
                    select(
                        OrderPaymentModel.payment_method_id,
                        func.sum(OrderPaymentModel.amount),
                    )
                    .join(OrderModel, OrderModel.id == OrderPaymentModel.order_id)
                    .where(
                        OrderModel.created_at >= opened,
                        OrderModel.created_at <= closed,
                        OrderModel.cancelled == False,  # noqa: E712
                    )
                    .group_by(OrderPaymentModel.payment_method_id)
                ).fetchall()
                return {str(row[0]): float(row[1]) for row in rows}
        finally:
            session.close()
