"""Regras do fiado/crediário (forma de pagamento e débitos de clientes)."""

from decimal import Decimal
from typing import Optional, Set

from billflux.services.text_normalize import strip_accents

FIADO_CANONICAL_NAME = "Fiado"
FIADO_ALIASES = {"fiado", "crediario"}


def is_fiado_name(name: Optional[str]) -> bool:
    """True se o nome da forma de pagamento identifica fiado/crediário."""
    if not name:
        return False
    normalized = strip_accents(name).strip().lower()
    return normalized in FIADO_ALIASES


def get_fiado_method_ids() -> Set[int]:
    """Ids das formas de pagamento que representam fiado/crediário."""
    from billflux.infra.repository.payment_method_repository import (
        PaymentMethodRepository,
    )

    return {
        m.id for m in PaymentMethodRepository().get_methods() if is_fiado_name(m.name)
    }


def ensure_fiado_method():
    """Garante que a forma 'Fiado' exista (cria se faltar)."""
    from billflux.infra.repository.payment_method_repository import (
        PaymentMethodRepository,
    )

    repository = PaymentMethodRepository()
    existing = [m for m in repository.get_methods() if is_fiado_name(m.name)]
    if existing:
        return existing[0]
    return repository.insert_method(name=FIADO_CANONICAL_NAME, sort_order=999)


def fiado_amount_for_order(order_id: int) -> Decimal:
    """Soma dos pagamentos de um pedido feitos na forma fiado."""
    from billflux.infra.config.database import get_session
    from billflux.infra.entities.order_payment import OrderPayment
    from billflux.infra.entities.payment_method import PaymentMethod
    from sqlmodel import select

    fiado_ids = get_fiado_method_ids()
    if not fiado_ids:
        return Decimal("0")

    session = get_session()
    try:
        with session:
            rows = session.exec(
                select(OrderPayment.amount, OrderPayment.payment_method_id).where(
                    OrderPayment.order_id == order_id
                )
            ).all()
            total = Decimal("0")
            for amount, method_id in rows:
                if method_id in fiado_ids:
                    total += Decimal(str(amount))
            return total
    finally:
        session.close()


def ensure_fiado_customer(selected_method_ids, customer_id):
    """Valida que venda fiada tem um cliente ativo vinculado.

    Levanta ValueError com as mesmas mensagens usadas no PDV; não faz
    nada quando nenhuma forma fiada foi selecionada."""
    if not get_fiado_method_ids().intersection(selected_method_ids or []):
        return
    if not customer_id:
        raise ValueError("Venda fiada: selecione o cliente para gerar o débito.")
    from billflux.infra.repository.customer_repository import CustomerRepository

    customer = CustomerRepository().get_customer(customer_id)
    if not customer or not customer.active:
        raise ValueError("Cliente inválido para venda fiada.")


def register_order_credit(order_id: int, customer_id: Optional[int]):
    """Cria o débito em contas a receber se o pedido tem parcela fiado."""
    total = fiado_amount_for_order(order_id)
    if total <= 0:
        return None
    from billflux.infra.repository.receivable_repository import (
        ReceivableRepository,
    )
    from billflux.services.audit import audit

    receivable = ReceivableRepository().create(
        order_id=order_id,
        customer_id=customer_id,
        amount=float(total),
        obs=f"Venda #{order_id}",
    )
    audit(
        "credit.sale",
        entity="order",
        entity_id=order_id,
        details={
            "customer_id": customer_id,
            "amount": round(float(total), 2),
        },
    )
    return receivable
