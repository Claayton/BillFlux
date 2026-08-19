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
