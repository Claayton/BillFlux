"""Repository for ProductUnit (apresentações de produto)"""

from typing import List, Optional

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.product_unit import ProductUnit as ProductUnitModel
from billflux.domain.models.product_units import ProductUnit


def _to_domain(pu: ProductUnitModel) -> ProductUnit:
    return ProductUnit(
        id=pu.id,
        product_id=pu.product_id,
        name=pu.name,
        barcode=pu.barcode,
        factor=pu.factor,
        price=pu.price,
        is_default=pu.is_default,
    )


class ProductUnitRepository:
    """ProductUnit data manipulation"""

    def get_units_for_product(self, product_id: int) -> List[ProductUnit]:
        session = get_session()
        try:
            with session:
                stmt = (
                    select(ProductUnitModel)
                    .where(ProductUnitModel.product_id == product_id)
                    .order_by(ProductUnitModel.is_default.desc(), ProductUnitModel.name)
                )
                return [_to_domain(pu) for pu in session.exec(stmt).all()]
        finally:
            session.close()

    def get_units_for_products(self, product_ids: List[int]) -> List[ProductUnit]:
        """Carrega apresentações de vários produtos de uma vez (batch)."""
        if not product_ids:
            return []
        session = get_session()
        try:
            with session:
                stmt = (
                    select(ProductUnitModel)
                    .where(ProductUnitModel.product_id.in_(product_ids))
                    .order_by(ProductUnitModel.is_default.desc(), ProductUnitModel.name)
                )
                return [_to_domain(pu) for pu in session.exec(stmt).all()]
        finally:
            session.close()

    def get_unit(self, unit_id: int) -> Optional[ProductUnit]:
        session = get_session()
        try:
            with session:
                pu = session.get(ProductUnitModel, unit_id)
                return _to_domain(pu) if pu else None
        finally:
            session.close()

    def get_unit_by_barcode(self, barcode: str) -> Optional[ProductUnit]:
        session = get_session()
        try:
            with session:
                stmt = select(ProductUnitModel).where(
                    ProductUnitModel.barcode == barcode
                )
                pu = session.exec(stmt).first()
                return _to_domain(pu) if pu else None
        finally:
            session.close()

    def upsert(
        self,
        product_id: int,
        name: str,
        barcode: Optional[str] = None,
        factor: int = 1,
        price=None,
        is_default: bool = False,
        unit_id: Optional[int] = None,
    ) -> ProductUnit:
        session = get_session()
        try:
            with session:
                if unit_id:
                    pu = session.get(ProductUnitModel, unit_id)
                    if not pu:
                        raise ValueError("Apresentação não encontrada.")
                else:
                    pu = ProductUnitModel(product_id=product_id)
                    session.add(pu)

                pu.name = name
                pu.barcode = barcode or None
                pu.factor = factor
                if price is not None:
                    pu.price = price
                pu.is_default = is_default

                if is_default:
                    stmt = select(ProductUnitModel).where(
                        ProductUnitModel.product_id == product_id,
                        ProductUnitModel.is_default == True,
                        ProductUnitModel.id != pu.id,
                    )
                    for old in session.exec(stmt).all():
                        old.is_default = False
                        session.add(old)

                session.commit()
                session.refresh(pu)
                return _to_domain(pu)
        finally:
            session.close()

    def delete(self, unit_id: int) -> bool:
        session = get_session()
        try:
            with session:
                pu = session.get(ProductUnitModel, unit_id)
                if pu and not pu.is_default:
                    session.delete(pu)
                    session.commit()
                    return True
                return False
        finally:
            session.close()

    def ensure_default_unit(self, product_id: int, price=None) -> ProductUnit:
        """Garante que todo produto tenha ao menos uma apresentação 'Unidade'."""
        units = self.get_units_for_product(product_id)
        if units:
            return units[0]
        return self.upsert(
            product_id=product_id,
            name="Unidade",
            factor=1,
            price=price or 0,
            is_default=True,
        )
