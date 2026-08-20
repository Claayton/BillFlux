"""Module for repository to Product (catálogo do PDV)"""

from decimal import Decimal
from typing import List, Optional

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.product import Product as ProductModel
from billflux.infra.entities.product_movement import (
    ProductMovement as ProductMovementModel,
)
from billflux.domain.models.products import Product
from billflux.domain.models.product_movements import ProductMovement


class ProductRepository:
    """Product table data manipulation"""

    def insert_product(
        self,
        name: str,
        price: Decimal,
        barcode: Optional[str] = None,
        stock_quantity: int = 0,
        min_stock: int = 0,
        active: bool = True,
        obs: Optional[str] = None,
        cost: Decimal = Decimal("0"),
    ) -> Product:
        """Inserts a new product into the Product table."""

        session = get_session()
        try:
            with session:
                product = ProductModel(
                    name=name,
                    price=price,
                    cost=cost,
                    barcode=barcode,
                    stock_quantity=stock_quantity,
                    min_stock=min_stock,
                    active=active,
                    obs=obs,
                )
                session.add(product)
                session.flush()
                if stock_quantity > 0:
                    session.add(
                        ProductMovementModel(
                            product_id=product.id,
                            movement_type="entrada",
                            quantity=stock_quantity,
                            obs="Estoque inicial",
                        )
                    )
                session.commit()
                session.refresh(product)
                return Product(**dict(product))
        finally:
            session.close()

    def get_products(self) -> List[Product]:
        """Returns all products (active first, then by name)."""

        session = get_session()
        try:
            with session:
                sql = select(ProductModel).order_by(
                    ProductModel.active.desc(), ProductModel.name
                )
                products = session.exec(sql).all()
                return [Product(**dict(product)) for product in products]
        finally:
            session.close()

    def get_active_products(self) -> List[Product]:
        """Returns only active products ordered by name."""

        session = get_session()
        try:
            with session:
                sql = (
                    select(ProductModel)
                    .where(ProductModel.active == True)  # noqa: E712
                    .order_by(ProductModel.name)
                )
                products = session.exec(sql).all()
                return [Product(**dict(product)) for product in products]
        finally:
            session.close()

    def get_product(self, product_id: int) -> Optional[Product]:
        """Returns a product by its id."""

        session = get_session()
        try:
            with session:
                product = session.get(ProductModel, product_id)
                return Product(**dict(product)) if product else None
        finally:
            session.close()

    def get_product_by_barcode(self, barcode: str) -> Optional[Product]:
        """Returns a product by its barcode."""

        session = get_session()
        try:
            with session:
                product = session.exec(
                    select(ProductModel).where(ProductModel.barcode == barcode)
                ).first()
                return Product(**dict(product)) if product else None
        finally:
            session.close()

    def update_product(self, product_id: int, **fields: object) -> Optional[Product]:
        """Updates the fields of an existing product."""

        session = get_session()
        try:
            with session:
                product = session.get(ProductModel, product_id)
                if not product:
                    return None
                for key, value in fields.items():
                    setattr(product, key, value)
                session.add(product)
                session.commit()
                session.refresh(product)
                return Product(**dict(product))
        finally:
            session.close()

    def delete_product(self, product_id: int) -> bool:
        """Deletes a product by its id."""

        session = get_session()
        try:
            with session:
                product = session.get(ProductModel, product_id)
                if not product:
                    return False
                session.delete(product)
                session.commit()
                return True
        finally:
            session.close()

    def adjust_stock(
        self,
        product_id: int,
        delta: int,
        obs: Optional[str] = None,
        movement_type: str = "ajuste",
    ) -> Optional[Product]:
        """Ajusta o estoque (positivo entra, negativo sai) e registra o movimento.
        Retorna None se o produto não existe ou o estoque ficaria negativo."""

        if delta == 0:
            return self.get_product(product_id)

        session = get_session()
        try:
            with session:
                product = session.get(ProductModel, product_id)
                if not product:
                    return None
                new_quantity = product.stock_quantity + delta
                if new_quantity < 0:
                    return None
                product.stock_quantity = new_quantity
                session.add(product)
                session.add(
                    ProductMovementModel(
                        product_id=product.id,
                        movement_type=movement_type,
                        quantity=delta,
                        obs=obs,
                    )
                )
                session.commit()
                session.refresh(product)
                return Product(**dict(product))
        finally:
            session.close()

    def count_orders(self, product_id: int) -> int:
        """Counts order items linked to a product."""

        from billflux.infra.entities.order_item import OrderItem

        session = get_session()
        try:
            with session:
                sql = select(OrderItem).where(OrderItem.product_id == product_id)
                return len(session.exec(sql).all())
        finally:
            session.close()

    def get_movements(self, product_id: int, limit: int = 10) -> List[ProductMovement]:
        """Returns the most recent stock movements of a product."""

        session = get_session()
        try:
            with session:
                sql = (
                    select(ProductMovementModel)
                    .where(ProductMovementModel.product_id == product_id)
                    .order_by(ProductMovementModel.created_at.desc())
                    .limit(limit)
                )
                movements = session.exec(sql).all()
                return [ProductMovement(**dict(movement)) for movement in movements]
        finally:
            session.close()
