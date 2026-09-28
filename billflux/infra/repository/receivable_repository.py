"""Module for repository to Receivable (contas a receber / fiado)"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.receivable import Receivable as ReceivableModel
from billflux.infra.entities.receivable_payment import (
    ReceivablePayment as ReceivablePaymentModel,
)
from billflux.infra.entities.customer import Customer as CustomerModel
from billflux.domain.models.receivables import (
    Receivable,
    ReceivablePayment,
)


def _balance(amount, paid_amount, cancelled) -> float:
    if cancelled:
        return 0.0
    return round(max(float(amount or 0) - float(paid_amount or 0), 0), 2)


def _to_domain(m: ReceivableModel, customer_name: str = "") -> Receivable:
    return Receivable(
        id=m.id,
        order_id=m.order_id,
        customer_id=m.customer_id,
        customer_name=customer_name,
        amount=m.amount,
        paid_amount=m.paid_amount,
        cancelled=m.cancelled,
        obs=m.obs,
        created_at=m.created_at,
    )


def _payment_to_domain(m: ReceivablePaymentModel) -> ReceivablePayment:
    return ReceivablePayment(
        id=m.id,
        receivable_id=m.receivable_id,
        method_id=m.method_id,
        amount=m.amount,
        cash_movement_id=m.cash_movement_id,
        created_by=m.created_by,
        created_at=m.created_at,
    )


class ReceivableRepository:
    """Receivable table data manipulation"""

    def create(
        self,
        order_id: Optional[int],
        customer_id: int,
        amount: float,
        obs: Optional[str] = None,
    ) -> Receivable:
        """Cria um débito (fiado) aberto para o cliente."""
        session = get_session()
        try:
            with session:
                model = ReceivableModel(
                    order_id=order_id,
                    customer_id=customer_id,
                    amount=Decimal(str(round(float(amount), 2))),
                    paid_amount=Decimal("0"),
                    obs=obs,
                )
                session.add(model)
                session.commit()
                session.refresh(model)
                return _to_domain(model)
        finally:
            session.close()

    def get(self, receivable_id: int) -> Optional[Receivable]:
        """Busca um débito com o nome do cliente."""
        session = get_session()
        try:
            with session:
                model = session.get(ReceivableModel, receivable_id)
                if not model:
                    return None
                customer = session.get(CustomerModel, model.customer_id)
                return _to_domain(model, customer.name if customer else "")
        finally:
            session.close()

    def get_by_order(self, order_id: int) -> Optional[Receivable]:
        """Último débito vinculado a um pedido (se houver)."""
        session = get_session()
        try:
            with session:
                model = session.exec(
                    select(ReceivableModel)
                    .where(ReceivableModel.order_id == order_id)
                    .order_by(ReceivableModel.id.desc())
                ).first()
                if not model:
                    return None
                customer = session.get(CustomerModel, model.customer_id)
                return _to_domain(model, customer.name if customer else "")
        finally:
            session.close()

    def list_receivables(
        self,
        status: str = "open",
        search: Optional[str] = None,
        customer_id: Optional[int] = None,
        limit: int = 200,
    ) -> List[Receivable]:
        """Lista débitos: 'open' (em aberto), 'paid' (quitados) ou 'all'."""
        session = get_session()
        try:
            with session:
                sql = (
                    select(ReceivableModel, CustomerModel.name)
                    .join(
                        CustomerModel, CustomerModel.id == ReceivableModel.customer_id
                    )
                    .order_by(
                        ReceivableModel.created_at.desc(), ReceivableModel.id.desc()
                    )
                )
                if customer_id is not None:
                    sql = sql.where(ReceivableModel.customer_id == customer_id)
                rows = session.exec(sql).all()

                items = []
                for model, customer_name in rows:
                    balance = _balance(model.amount, model.paid_amount, model.cancelled)
                    if status == "open" and (model.cancelled or balance <= 0):
                        continue
                    if status == "paid" and (model.cancelled or balance > 0):
                        continue
                    if search and search.lower() not in (customer_name or "").lower():
                        continue
                    items.append(_to_domain(model, customer_name))
                    if len(items) >= limit:
                        break
                return items
        finally:
            session.close()

    def add_payment(
        self,
        receivable_id: int,
        amount: float,
        method_id: Optional[int],
        created_by: str,
        cash_movement_id: Optional[int] = None,
    ) -> Receivable:
        """Registra um recebimento sobre o débito (valida saldo em aberto)."""
        value = round(float(amount), 2)
        session = get_session()
        try:
            with session:
                model = session.get(ReceivableModel, receivable_id)
                if not model:
                    raise ValueError("Débito não encontrado.")
                if model.cancelled:
                    raise ValueError("Débito cancelado.")
                balance = _balance(model.amount, model.paid_amount, False)
                if balance <= 0:
                    raise ValueError("Débito já quitado.")
                if value <= 0:
                    raise ValueError("Informe um valor maior que zero.")
                if value > balance + 0.009:
                    raise ValueError(
                        f"Valor acima do saldo em aberto (R$ {balance:.2f})."
                    )

                model.paid_amount = Decimal(
                    str(round(float(model.paid_amount) + value, 2))
                )
                session.add(model)
                session.add(
                    ReceivablePaymentModel(
                        receivable_id=model.id,
                        method_id=method_id,
                        amount=Decimal(str(value)),
                        cash_movement_id=cash_movement_id,
                        created_by=created_by,
                    )
                )
                session.commit()
                session.refresh(model)
                customer = session.get(CustomerModel, model.customer_id)
                return _to_domain(model, customer.name if customer else "")
        finally:
            session.close()

    def attach_cash_movement(self, receivable_id: int, cash_movement_id: int) -> None:
        """Vincula o recebimento mais recente do débito à movimentação de caixa."""
        session = get_session()
        try:
            with session:
                row = session.exec(
                    select(ReceivablePaymentModel)
                    .where(ReceivablePaymentModel.receivable_id == receivable_id)
                    .order_by(ReceivablePaymentModel.id.desc())
                ).first()
                if row:
                    row.cash_movement_id = cash_movement_id
                    session.add(row)
                    session.commit()
        finally:
            session.close()

    def cancel_by_order(
        self, order_id: int, reason: Optional[str] = None
    ) -> Optional[Receivable]:
        """Cancela o débito de um pedido (ex.: venda estornada)."""
        session = get_session()
        try:
            with session:
                rows = session.exec(
                    select(ReceivableModel).where(
                        ReceivableModel.order_id == order_id,
                        ReceivableModel.cancelled == False,  # noqa: E712
                    )
                ).all()
                if not rows:
                    return None
                model = rows[0]
                model.cancelled = True
                if reason:
                    model.obs = (model.obs + " | " if model.obs else "") + reason
                session.add(model)
                session.commit()
                session.refresh(model)
                customer = session.get(CustomerModel, model.customer_id)
                return _to_domain(model, customer.name if customer else "")
        finally:
            session.close()

    def customer_balances(self) -> Dict[int, float]:
        """Saldo devedor em aberto por cliente_id."""
        session = get_session()
        try:
            with session:
                rows = session.exec(select(ReceivableModel)).all()
                balances: Dict[int, float] = {}
                for model in rows:
                    balance = _balance(model.amount, model.paid_amount, model.cancelled)
                    if balance > 0:
                        balances[model.customer_id] = round(
                            balances.get(model.customer_id, 0.0) + balance, 2
                        )
                return balances
        finally:
            session.close()

    def totals(self) -> Dict[str, float]:
        """Resumo geral dos débitos (abertos, quitados e clientes devedores)."""
        session = get_session()
        try:
            with session:
                rows = session.exec(select(ReceivableModel)).all()
                open_amount = 0.0
                open_count = 0
                paid_amount = 0.0
                paid_count = 0
                debtors = set()
                for model in rows:
                    if model.cancelled:
                        continue
                    balance = _balance(model.amount, model.paid_amount, False)
                    amount = float(model.amount or 0)
                    paid = float(model.paid_amount or 0)
                    if balance > 0:
                        open_amount = round(open_amount + balance, 2)
                        open_count += 1
                        debtors.add(model.customer_id)
                    elif paid >= amount and amount > 0:
                        paid_amount = round(paid_amount + paid, 2)
                        paid_count += 1
                return {
                    "open_amount": open_amount,
                    "open_count": open_count,
                    "paid_count": paid_count,
                    "customers": len(debtors),
                }
        finally:
            session.close()

    def list_payments(self, receivable_id: int) -> List[ReceivablePayment]:
        """Histórico de recebimentos de um débito."""
        session = get_session()
        try:
            with session:
                rows = session.exec(
                    select(ReceivablePaymentModel)
                    .where(ReceivablePaymentModel.receivable_id == receivable_id)
                    .order_by(ReceivablePaymentModel.id.desc())
                ).all()
                return [_payment_to_domain(m) for m in rows]
        finally:
            session.close()
