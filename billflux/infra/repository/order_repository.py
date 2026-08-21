"""Module for repository to Order (pedidos do PDV)"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.order import Order as OrderModel
from billflux.infra.entities.order_item import OrderItem as OrderItemModel
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
    ) -> Order:
        """Cria um pedido de forma transacional: pedido + itens + baixa de estoque
        + log de movimentação. Levanta ValueError se um produto não existir,
        estiver inativo ou tiver estoque insuficiente (nada é persistido)."""

        session = get_session()
        try:
            with session:
                products = []
                total = Decimal("0")
                for product_id, quantity in items:
                    if quantity <= 0:
                        raise ValueError("Quantidade inválida.")
                    product = session.get(ProductModel, product_id)
                    if not product or not product.active:
                        raise ValueError("Produto não encontrado.")
                    if product.stock_quantity < quantity:
                        raise ValueError(f"Estoque insuficiente para {product.name}.")
                    products.append((product, quantity))
                    total += product.price * quantity

                order = OrderModel(
                    total=total, payment_method_id=payment_method_id, obs=obs
                )
                session.add(order)
                session.flush()

                for product, quantity in products:
                    session.add(
                        OrderItemModel(
                            order_id=order.id,
                            product_id=product.id,
                            quantity=quantity,
                            unit_price=product.price,
                        )
                    )
                    product.stock_quantity -= quantity
                    session.add(product)
                    session.add(
                        ProductMovementModel(
                            product_id=product.id,
                            movement_type="saida",
                            quantity=quantity,
                            obs=f"Venda #{order.id}",
                        )
                    )
                session.commit()
                session.refresh(order)
                return Order(**dict(order))
        finally:
            session.close()

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

    def delete_order(self, order_id: int) -> bool:
        """Cancela um pedido restaurando o estoque dos itens e o log.

        Devolve as quantidades ao estoque com movimentação de entrada e remove
        o pedido e seus itens. Tudo numa única transação."""

        session = get_session()
        try:
            with session:
                order = session.get(OrderModel, order_id)
                if not order:
                    return False
                order_items = session.exec(
                    select(OrderItemModel).where(OrderItemModel.order_id == order_id)
                ).all()
                for item in order_items:
                    product = session.get(ProductModel, item.product_id)
                    if product:
                        product.stock_quantity += item.quantity
                        session.add(product)
                        session.add(
                            ProductMovementModel(
                                product_id=item.product_id,
                                movement_type="entrada",
                                quantity=item.quantity,
                                obs=f"Venda #{order_id} cancelada",
                            )
                        )
                    session.delete(item)
                session.delete(order)
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
    ) -> Order:
        """Atualiza um pedido de forma transacional, mantendo o mesmo id.

        Valida os itens novos, devolve o estoque do que saiu/reduziu e baixa o
        estoque do que entrou/aumentou, registrando as movimentações. Levanta
        ValueError se um produto não existir, estiver inativo ou sem estoque
        (nada é persistido)."""

        session = get_session()
        try:
            with session:
                order = session.get(OrderModel, order_id)
                if not order:
                    raise ValueError("Pedido não encontrado.")

                new_products = []
                total = Decimal("0")
                for product_id, quantity in items:
                    if quantity <= 0:
                        raise ValueError("Quantidade inválida.")
                    product = session.get(ProductModel, product_id)
                    if not product or not product.active:
                        raise ValueError("Produto não encontrado.")
                    new_products.append((product, quantity))
                    total += product.price * quantity

                old_items = session.exec(
                    select(OrderItemModel).where(OrderItemModel.order_id == order_id)
                ).all()
                old_by_product = {item.product_id: item for item in old_items}

                # Estoque suficiente considerando o delta (o que já estava no
                # pedido será devolvido antes da nova baixa).
                for product, quantity in new_products:
                    old_item = old_by_product.get(product.id)
                    old_qty = old_item.quantity if old_item else 0
                    needed = quantity - old_qty
                    if needed > product.stock_quantity:
                        raise ValueError(f"Estoque insuficiente para {product.name}.")

                new_product_ids = set()
                for product, quantity in new_products:
                    old_item = old_by_product.get(product.id)
                    old_qty = old_item.quantity if old_item else 0
                    delta = quantity - old_qty
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
                    if old_item:
                        old_item.quantity = quantity
                        old_item.unit_price = product.price
                        session.add(old_item)
                    else:
                        session.add(
                            OrderItemModel(
                                order_id=order_id,
                                product_id=product.id,
                                quantity=quantity,
                                unit_price=product.price,
                            )
                        )
                    new_product_ids.add(product.id)

                # Itens que saíram do pedido: devolve o estoque e remove.
                for old_item in old_items:
                    if old_item.product_id not in new_product_ids:
                        product = session.get(ProductModel, old_item.product_id)
                        if product:
                            product.stock_quantity += old_item.quantity
                            session.add(product)
                            session.add(
                                ProductMovementModel(
                                    product_id=old_item.product_id,
                                    movement_type="entrada",
                                    quantity=old_item.quantity,
                                    obs=f"Venda #{order_id} editada",
                                )
                            )
                        session.delete(old_item)

                order.total = total
                order.payment_method_id = payment_method_id
                order.obs = obs
                session.add(order)
                session.commit()
                session.refresh(order)
                return Order(**dict(order))
        finally:
            session.close()
