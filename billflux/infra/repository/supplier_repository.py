"""Module for repository to Supplier (fornecedores)"""

from typing import List, Optional

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.supplier import Supplier as SupplierModel
from billflux.domain.models.suppliers import Supplier


def _to_domain(s: SupplierModel) -> Supplier:
    return Supplier(**dict(s))


def _to_domains(items: List[SupplierModel]) -> List[Supplier]:
    return [_to_domain(item) for item in items]


class SupplierRepository:
    """Supplier table data manipulation"""

    def insert_supplier(self, **fields) -> Supplier:
        session = get_session()
        try:
            with session:
                supplier = SupplierModel(**fields)
                session.add(supplier)
                session.commit()
                session.refresh(supplier)
                return _to_domain(supplier)
        finally:
            session.close()

    def get_suppliers(
        self,
        search: Optional[str] = None,
        active_only: bool = False,
    ) -> List[Supplier]:
        session = get_session()
        try:
            with session:
                sql = select(SupplierModel)
                if active_only:
                    sql = sql.where(SupplierModel.active == True)  # noqa: E712
                if search:
                    like = f"%{search}%"
                    sql = sql.where(
                        SupplierModel.name.ilike(like)
                        | SupplierModel.cnpj.ilike(like)
                        | SupplierModel.phone.ilike(like)
                    )
                sql = sql.order_by(SupplierModel.name)
                return _to_domains(session.exec(sql).all())
        finally:
            session.close()

    def get_supplier(self, supplier_id: int) -> Optional[Supplier]:
        session = get_session()
        try:
            with session:
                s = session.get(SupplierModel, supplier_id)
                return _to_domain(s) if s else None
        finally:
            session.close()

    def get_supplier_by_cnpj(self, cnpj: str) -> Optional[Supplier]:
        session = get_session()
        try:
            with session:
                sql = select(SupplierModel).where(SupplierModel.cnpj == cnpj)
                s = session.exec(sql).first()
                return _to_domain(s) if s else None
        finally:
            session.close()

    def update_supplier(self, supplier_id: int, **fields) -> Optional[Supplier]:
        session = get_session()
        try:
            with session:
                s = session.get(SupplierModel, supplier_id)
                if not s:
                    return None
                for key, value in fields.items():
                    setattr(s, key, value)
                session.add(s)
                session.commit()
                session.refresh(s)
                return _to_domain(s)
        finally:
            session.close()

    def delete_supplier(self, supplier_id: int) -> bool:
        session = get_session()
        try:
            with session:
                s = session.get(SupplierModel, supplier_id)
                if not s:
                    return False
                session.delete(s)
                session.commit()
                return True
        finally:
            session.close()

    def toggle_active(self, supplier_id: int) -> Optional[Supplier]:
        session = get_session()
        try:
            with session:
                s = session.get(SupplierModel, supplier_id)
                if not s:
                    return None
                s.active = not s.active
                session.add(s)
                session.commit()
                session.refresh(s)
                return _to_domain(s)
        finally:
            session.close()
