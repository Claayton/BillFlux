"""Module for repository to Order (pedidos do PDV)"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.order import Order as OrderModel
from billflux.infra.entities.order_item import OrderItem as OrderItemModel
from billflux.infra.entities.order_payment import (
    OrderPayment as OrderPaymentModel,
)
from billflux.infra.entities.product import Product as ProductModel
from billflux.infra.entities.product_movement import (
    ProductMovement as ProductMovementModel,
)
from billflux.domain.models.orders import Order
from billflux.domain.models.order_items import OrderItem


class OrderRepository:
    """Order table data manipulation"""

    def create_order(
        self,
        items: List[tuple],
        payment_method_id: int,
        obs: Optional[str] = None,
        discount: Optional[Decimal] = None,
        payments: Optional[List[tuple]] = None,
        customer_id: Optional[int] = None,
    ) -> Order:
        """Cria um pedido de forma transacional: pedido + itens + baixa de estoque
        + log de movimentação. Levanta ValueError se um produto não existir ou
        estiver inativo (nada é persistido). O estoque pode ficar negativo
        (venda sem estoque é permitida). O desconto (em R$) é abatido do total.
        `payments` é uma lista de (payment_method_id, valor); se não informada,
        usa um único pagamento na forma indicada pelo total.
        Cada item é (product_id, quantidade) ou, opcionalmente,
        (product_id, quantidade, preço_unitário, fator). A quantidade/preço são
        da apresentação vendida e o fator converte pra unidades-base no estoque
        (ex.: 1 caixa a R$ 45,99 com fator 15). Sem o preço, usa o preço base do
        produto; sem o fator, assume 1."""

        session = get_session()
        try:
            with session:
                order = self._create_order_in_session(
                    session,
                    items,
                    payment_method_id,
                    obs=obs,
                    discount=discount,
                    payments=payments,
                    customer_id=customer_id,
                    decrement_stock=True,
                )
                session.commit()
                session.refresh(order)
                return Order(**dict(order))
        finally:
            session.close()

    @staticmethod
    def _create_order_in_session(
        session,
        items: List[tuple],
        payment_method_id: int,
        obs: Optional[str] = None,
        discount: Optional[Decimal] = None,
        payments: Optional[List[tuple]] = None,
        customer_id: Optional[int] = None,
        *,
        decrement_stock: bool = True,
        allow_inactive: bool = False,
    ):
        """Cria o pedido dentro da transação do chamador (sem commit).
        Com `decrement_stock=False` não mexe no estoque (baixa já feita
        antes, ex.: comanda); com `allow_inactive=True` aceita produto
        inativo (mercadoria já entregue na comanda)."""

        products = []
        subtotal = Decimal("0")
        for entry in items:
            product_id = entry[0]
            quantity = entry[1]
            price_override = entry[2] if len(entry) > 2 else None
            factor = int(entry[3]) if len(entry) > 3 and entry[3] else 1
            if quantity <= 0:
                raise ValueError("Quantidade inválida.")
            if factor < 1:
                factor = 1
            product = session.get(ProductModel, product_id)
            if not product or (not allow_inactive and not product.active):
                raise ValueError("Produto não encontrado.")
            unit_price = (
                Decimal(str(price_override))
                if price_override is not None
                else product.price
            )
            products.append((product, quantity, unit_price, factor))
            subtotal += unit_price * quantity

        discount = discount or Decimal("0")
        total = subtotal - discount
        if total < 0:
            total = Decimal("0")

        payments = OrderRepository._normalize_payments(
            session, payments, payment_method_id, total
        )

        order = OrderModel(
            total=total,
            payment_method_id=payments[0][0],
            obs=obs,
            discount=discount or None,
            customer_id=customer_id,
        )
        session.add(order)
        session.flush()

        OrderRepository._insert_payments(session, order.id, payments)

        for product, quantity, unit_price, factor in products:
            session.add(
                OrderItemModel(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=unit_price,
                    factor=factor,
                )
            )
            if decrement_stock:
                base_quantity = quantity * factor
                product.stock_quantity -= base_quantity
                session.add(product)
                session.add(
                    ProductMovementModel(
                        product_id=product.id,
                        movement_type="saida",
                        quantity=base_quantity,
                        obs=f"Venda #{order.id}",
                    )
                )
        return order

    def get_orders(self) -> List[Order]:
        """Returns all orders, newest first."""

        session = get_session()
        try:
            with session:
                sql = select(OrderModel).order_by(OrderModel.created_at.desc())
                orders = session.exec(sql).all()
                return [Order(**dict(order)) for order in orders]
        finally:
            session.close()

    def get_orders_by_customer(self, customer_id: int) -> List[Order]:
        """Returns orders for a specific customer, newest first."""

        session = get_session()
        try:
            with session:
                sql = (
                    select(OrderModel)
                    .where(OrderModel.customer_id == customer_id)
                    .order_by(OrderModel.created_at.desc())
                )
                orders = session.exec(sql).all()
                return [Order(**dict(order)) for order in orders]
        finally:
            session.close()

    def get_orders_by_date(self, day: date) -> List[Order]:
        """Returns the orders of a specific day."""

        start = datetime.combine(day, datetime.min.time())
        end = datetime.combine(day, datetime.max.time())
        session = get_session()
        try:
            with session:
                sql = (
                    select(OrderModel)
                    .where(
                        OrderModel.created_at >= start,
                        OrderModel.created_at <= end,
                    )
                    .order_by(OrderModel.created_at.desc())
                )
                orders = session.exec(sql).all()
                return [Order(**dict(order)) for order in orders]
        finally:
            session.close()

    def get_order(self, order_id: int) -> Optional[Order]:
        """Returns an order by its id."""

        session = get_session()
        try:
            with session:
                order = session.get(OrderModel, order_id)
                return Order(**dict(order)) if order else None
        finally:
            session.close()

    def get_order_items(self, order_id: int) -> List[OrderItem]:
        """Returns the items of an order."""

        session = get_session()
        try:
            with session:
                sql = select(OrderItemModel).where(OrderItemModel.order_id == order_id)
                items = session.exec(sql).all()
                return [OrderItem(**dict(item)) for item in items]
        finally:
            session.close()

    def get_order_payments(self, order_id: int) -> List[tuple]:
        """Returns the payments (method_id, amount) of an order."""

        session = get_session()
        try:
            with session:
                sql = select(OrderPaymentModel).where(
                    OrderPaymentModel.order_id == order_id
                )
                payments = session.exec(sql).all()
                return [(p.payment_method_id, p.amount) for p in payments]
        finally:
            session.close()

    @staticmethod
    def _normalize_payments(session, payments, payment_method_id, total):
        """Valida a lista de pagamentos (method_id, valor) e a usa, ou cria um
        único pagamento na forma indicada pelo total."""

        from billflux.infra.entities.payment_method import (
            PaymentMethod as PaymentMethodModel,
        )

        if payments is None:
            payments = [(payment_method_id, total)]

        normalized = []
        received = Decimal("0")
        for method_id, amount in payments:
            method = session.get(PaymentMethodModel, method_id)
            if not method or not method.active:
                raise ValueError("Forma de pagamento inválida.")
            amount = Decimal(str(amount))
            if amount <= 0:
                raise ValueError("Valor de pagamento inválido.")
            normalized.append((method_id, amount))
            received += amount

        if received < total:
            raise ValueError("Valores de pagamento insuficientes.")
        return normalized

    @staticmethod
    def _insert_payments(session, order_id, payments):
        for method_id, amount in payments:
            session.add(
                OrderPaymentModel(
                    order_id=order_id,
                    payment_method_id=method_id,
                    amount=amount,
                )
            )

    def _replace_payments(self, session, order_id, payments):
        old = session.exec(
            select(OrderPaymentModel).where(OrderPaymentModel.order_id == order_id)
        ).all()
        for payment in old:
            session.delete(payment)
        self._insert_payments(session, order_id, payments)

    def cancel_order(self, order_id: int) -> bool:
        """Cancela um pedido mantendo-o na lista: marca como cancelado e
        restaura o estoque dos itens com movimentação de entrada.

        Devolve False se o pedido não existe ou já está cancelado."""

        session = get_session()
        try:
            with session:
                order = session.get(OrderModel, order_id)
                if not order or order.cancelled:
                    return False
                order.cancelled = True
                session.add(order)
                order_items = session.exec(
                    select(OrderItemModel).where(OrderItemModel.order_id == order_id)
                ).all()
                for item in order_items:
                    product = session.get(ProductModel, item.product_id)
                    if product:
                        base_quantity = item.quantity * (item.factor or 1)
                        product.stock_quantity += base_quantity
                        session.add(product)
                        session.add(
                            ProductMovementModel(
                                product_id=item.product_id,
                                movement_type="entrada",
                                quantity=base_quantity,
                                obs=f"Venda #{order_id} cancelada",
                            )
                        )
                session.commit()
                return True
        finally:
            session.close()

    def update_order(
        self,
        order_id: int,
        items: List[tuple],
        payment_method_id: int,
        obs: Optional[str] = None,
        discount: Optional[Decimal] = None,
        payments: Optional[List[tuple]] = None,
    ) -> Order:
        """Atualiza um pedido de forma transacional, mantendo o mesmo id.

        Valida os itens novos, devolve o estoque do que saiu/reduziu e baixa o
        estoque do que entrou/aumentou, registrando as movimentações. Levanta
        ValueError se um produto não existir, estiver inativo ou sem estoque
        (nada é persistido). O desconto (em R$) é abatido do total; se não
        informado, mantém o desconto atual."""

        session = get_session()
        try:
            with session:
                order = session.get(OrderModel, order_id)
                if not order:
                    raise ValueError("Pedido não encontrado.")
                if order.cancelled:
                    raise ValueError("Venda cancelada não pode ser editada.")

                new_items = []
                subtotal = Decimal("0")
                for product_id, quantity in items:
                    if quantity <= 0:
                        raise ValueError("Quantidade inválida.")
                    product = session.get(ProductModel, product_id)
                    if not product or not product.active:
                        raise ValueError("Produto não encontrado.")
                    new_items.append((product, quantity))

                old_items = session.exec(
                    select(OrderItemModel).where(OrderItemModel.order_id == order_id)
                ).all()
                old_by_product = {item.product_id: item for item in old_items}

                # Resolve preço/fator: mantém o snapshot de quem já estava no
                # pedido (apresentação vendida) e usa o preço base do produto
                # para itens adicionados agora na edição.
                resolved = []
                for product, quantity in new_items:
                    old_item = old_by_product.get(product.id)
                    if old_item:
                        unit_price = old_item.unit_price
                        factor = old_item.factor or 1
                        old_base = old_item.quantity * factor
                    else:
                        unit_price = product.price
                        factor = 1
                        old_base = 0
                    resolved.append(
                        (
                            product,
                            quantity,
                            unit_price,
                            factor,
                            old_base,
                            quantity * factor,
                        )
                    )
                    subtotal += unit_price * quantity

                # Estoque suficiente considerando o delta (o que já estava no
                # pedido será devolvido antes da nova baixa).
                for product, _q, _p, _f, old_base, new_base in resolved:
                    needed = new_base - old_base
                    if needed > product.stock_quantity:
                        raise ValueError(f"Estoque insuficiente para {product.name}.")

                new_product_ids = set()
                for (
                    product,
                    quantity,
                    unit_price,
                    factor,
                    old_base,
                    new_base,
                ) in resolved:
                    delta = new_base - old_base
                    if delta:
                        product.stock_quantity -= delta
                        session.add(product)
                        session.add(
                            ProductMovementModel(
                                product_id=product.id,
                                movement_type="saida" if delta > 0 else "entrada",
                                quantity=abs(delta),
                                obs=f"Venda #{order_id} editada",
                            )
                        )
                    old_item = old_by_product.get(product.id)
                    if old_item:
                        old_item.quantity = quantity
                        old_item.unit_price = unit_price
                        old_item.factor = factor
                        session.add(old_item)
                    else:
                        session.add(
                            OrderItemModel(
                                order_id=order_id,
                                product_id=product.id,
                                quantity=quantity,
                                unit_price=unit_price,
                                factor=factor,
                            )
                        )
                    new_product_ids.add(product.id)

                # Itens que saíram do pedido: devolve o estoque e remove.
                for old_item in old_items:
                    if old_item.product_id not in new_product_ids:
                        product = session.get(ProductModel, old_item.product_id)
                        if product:
                            base_quantity = old_item.quantity * (old_item.factor or 1)
                            product.stock_quantity += base_quantity
                            session.add(product)
                            session.add(
                                ProductMovementModel(
                                    product_id=old_item.product_id,
                                    movement_type="entrada",
                                    quantity=base_quantity,
                                    obs=f"Venda #{order_id} editada",
                                )
                            )
                        session.delete(old_item)

                if discount is None:
                    discount = order.discount or Decimal("0")
                final_total = subtotal - discount
                if final_total < 0:
                    final_total = Decimal("0")
                payments = self._normalize_payments(
                    session, payments, payment_method_id, final_total
                )
                self._replace_payments(session, order_id, payments)
                order.total = final_total
                order.discount = discount or None
                order.payment_method_id = payments[0][0]
                order.obs = obs
                session.add(order)
                session.commit()
                session.refresh(order)
                return Order(**dict(order))
        finally:
            session.close()
