"""Repository for ProductSupplier (many-to-many product ↔ supplier with schedule)"""

import json
from typing import List, Optional

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.product_supplier import (
    ProductSupplier as ProductSupplierModel,
)
from billflux.infra.entities.supplier import Supplier as SupplierModel
from billflux.infra.entities.product import Product as ProductModel
from billflux.domain.models.product_suppliers import ProductSupplier


def _parse_days(ps: ProductSupplierModel) -> tuple:
    """Dias de entrega (0=domingo…6=sábado) com fallback pro campo antigo."""
    raw = getattr(ps, "delivery_days", None)
    if raw:
        try:
            days = json.loads(raw)
            if isinstance(days, list):
                return tuple(sorted({int(d) for d in days if 0 <= int(d) <= 6}))
        except (ValueError, TypeError):
            pass
    return (ps.delivery_day,)


def _to_domain(
    ps: ProductSupplierModel, supplier_name: str = "", product_name: str = ""
) -> ProductSupplier:
    return ProductSupplier(
        id=ps.id,
        product_id=ps.product_id,
        supplier_id=ps.supplier_id,
        supplier_name=supplier_name,
        product_name=product_name,
        delivery_day=ps.delivery_day,
        lead_time=ps.lead_time,
        is_primary=ps.is_primary,
        frequency=getattr(ps, "frequency", "semanal") or "semanal",
        week_parity=getattr(ps, "week_parity", 0) or 0,
        delivery_days=_parse_days(ps),
    )


class ProductSupplierRepository:
    """ProductSupplier data manipulation"""

    def get_suppliers_for_product(self, product_id: int) -> List[ProductSupplier]:
        session = get_session()
        try:
            with session:
                stmt = (
                    select(ProductSupplierModel, SupplierModel.name)
                    .join(
                        SupplierModel,
                        ProductSupplierModel.supplier_id == SupplierModel.id,
                    )
                    .where(ProductSupplierModel.product_id == product_id)
                )
                results = session.exec(stmt).all()
                return [_to_domain(ps, supplier_name=sname) for ps, sname in results]
        finally:
            session.close()

    def get_products_for_supplier(
        self, supplier_id: int, delivery_day: Optional[int] = None
    ) -> List[ProductSupplier]:
        session = get_session()
        try:
            with session:
                stmt = (
                    select(ProductSupplierModel, ProductModel.name)
                    .join(
                        ProductModel, ProductSupplierModel.product_id == ProductModel.id
                    )
                    .where(ProductSupplierModel.supplier_id == supplier_id)
                )
                results = session.exec(stmt).all()
                domain = [_to_domain(ps, product_name=pname) for ps, pname in results]
                if delivery_day is not None:
                    domain = [ps for ps in domain if delivery_day in ps.delivery_days]
                return domain
        finally:
            session.close()

    def get_by_product_and_supplier(
        self, product_id: int, supplier_id: int
    ) -> Optional[ProductSupplier]:
        session = get_session()
        try:
            with session:
                stmt = select(ProductSupplierModel).where(
                    ProductSupplierModel.product_id == product_id,
                    ProductSupplierModel.supplier_id == supplier_id,
                )
                ps = session.exec(stmt).first()
                if ps:
                    return _to_domain(ps)
                return None
        finally:
            session.close()

    def get_all_for_day(self, delivery_day: int) -> List[ProductSupplier]:
        session = get_session()
        try:
            with session:
                stmt = (
                    select(ProductSupplierModel, SupplierModel.name, ProductModel.name)
                    .join(
                        SupplierModel,
                        ProductSupplierModel.supplier_id == SupplierModel.id,
                    )
                    .join(
                        ProductModel, ProductSupplierModel.product_id == ProductModel.id
                    )
                )
                results = session.exec(stmt).all()
                domain = [
                    _to_domain(ps, supplier_name=sname, product_name=pname)
                    for ps, sname, pname in results
                ]
                # Cada vínculo tem uma lista de dias; filtra pela presença.
                return [ps for ps in domain if delivery_day in ps.delivery_days]
        finally:
            session.close()

    def upsert(
        self,
        product_id: int,
        supplier_id: int,
        delivery_day: int,
        delivery_days: Optional[list] = None,
        lead_time: int = 1,
        is_primary: bool = False,
        frequency: str = "semanal",
        week_parity: int = 0,
    ) -> ProductSupplier:
        days = tuple(
            sorted({int(d) for d in (delivery_days or []) if 0 <= int(d) <= 6})
        )
        if not days:
            days = (int(delivery_day),)
        primary_day = days[0]
        days_json = json.dumps(list(days))
        session = get_session()
        try:
            with session:
                stmt = select(ProductSupplierModel).where(
                    ProductSupplierModel.product_id == product_id,
                    ProductSupplierModel.supplier_id == supplier_id,
                )
                existing = session.exec(stmt).first()
                if existing:
                    existing.delivery_day = primary_day
                    existing.delivery_days = days_json
                    existing.lead_time = lead_time
                    existing.is_primary = is_primary
                    existing.frequency = frequency
                    existing.week_parity = week_parity
                    session.add(existing)
                    session.commit()
                    session.refresh(existing)
                    return _to_domain(existing)
                else:
                    if is_primary:
                        stmt_primary = select(ProductSupplierModel).where(
                            ProductSupplierModel.product_id == product_id,
                            ProductSupplierModel.is_primary.is_(True),
                        )
                        for old_primary in session.exec(stmt_primary).all():
                            old_primary.is_primary = False
                            session.add(old_primary)
                    ps = ProductSupplierModel(
                        product_id=product_id,
                        supplier_id=supplier_id,
                        delivery_day=primary_day,
                        delivery_days=days_json,
                        lead_time=lead_time,
                        is_primary=is_primary,
                        frequency=frequency,
                        week_parity=week_parity,
                    )
                    session.add(ps)
                    session.commit()
                    session.refresh(ps)
                    return _to_domain(ps)
        finally:
            session.close()

    def delete(self, product_supplier_id: int) -> bool:
        session = get_session()
        try:
            with session:
                ps = session.get(ProductSupplierModel, product_supplier_id)
                if ps:
                    session.delete(ps)
                    session.commit()
                    return True
                return False
        finally:
            session.close()
