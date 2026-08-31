"""Module for repository to Product (catálogo do PDV)"""

from decimal import Decimal
from typing import List, Optional

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.product import Product as ProductModel
from billflux.infra.entities.product_movement import (
    ProductMovement as ProductMovementModel,
)
from billflux.infra.entities.category import Category as CategoryModel
from billflux.infra.entities.supplier import Supplier as SupplierModel
from billflux.domain.models.products import Product
from billflux.domain.models.product_movements import ProductMovement


def _to_domain(product: ProductModel) -> Product:
    """Mapeia a entidade para o domínio, anexando o nome da categoria e fornecedor."""

    data = dict(product)
    data.pop("category", None)  # texto legado
    data["category_name"] = None
    if data.get("category_id"):
        session = get_session()
        try:
            category = session.get(CategoryModel, data["category_id"])
            data["category_name"] = category.name if category else None
        finally:
            session.close()
    data["supplier_name"] = None
    if data.get("supplier_id"):
        session = get_session()
        try:
            supplier = session.get(SupplierModel, data["supplier_id"])
            data["supplier_name"] = supplier.name if supplier else None
        finally:
            session.close()
    return Product(**data)


def _to_domains(products: List[ProductModel]) -> List[Product]:
    """Mapeia várias entidades, buscando os nomes das categorias e fornecedores em lote."""

    if not products:
        return []
    cat_ids = {p.category_id for p in products if p.category_id}
    cat_names = {}
    if cat_ids:
        session = get_session()
        try:
            sql = select(CategoryModel).where(CategoryModel.id.in_(cat_ids))
            cat_names = {c.id: c.name for c in session.exec(sql).all()}
        finally:
            session.close()
    sup_ids = {p.supplier_id for p in products if p.supplier_id}
    sup_names = {}
    if sup_ids:
        session = get_session()
        try:
            sql = select(SupplierModel).where(SupplierModel.id.in_(sup_ids))
            sup_names = {s.id: s.name for s in session.exec(sql).all()}
        finally:
            session.close()
    result = []
    for product in products:
        data = dict(product)
        data.pop("category", None)
        data["category_name"] = cat_names.get(data.get("category_id"))
        data["supplier_name"] = sup_names.get(data.get("supplier_id"))
        result.append(Product(**data))
    return result


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
        secondary_code: Optional[str] = None,
        category_id: Optional[int] = None,
        suppliers: Optional[str] = None,
        supplier_id: Optional[int] = None,
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
                    secondary_code=secondary_code,
                    category_id=category_id,
                    suppliers=suppliers,
                    supplier_id=supplier_id,
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
                return _to_domain(product)
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
                return _to_domains(products)
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
                return _to_domains(products)
        finally:
            session.close()

    def get_product(self, product_id: int) -> Optional[Product]:
        """Returns a product by its id."""

        session = get_session()
        try:
            with session:
                product = session.get(ProductModel, product_id)
                return _to_domain(product) if product else None
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
                return _to_domain(product) if product else None
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
                return _to_domain(product)
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
                return _to_domain(product)
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
