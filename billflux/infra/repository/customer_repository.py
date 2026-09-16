"""Module for repository to Customer (clientes)"""

from typing import List, Optional

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.customer import Customer as CustomerModel
from billflux.domain.models.customers import Customer
from billflux.services.text_normalize import strip_accents


def _to_domain(c: CustomerModel) -> Customer:
    return Customer(**dict(c))


def _to_domains(items: List[CustomerModel]) -> List[Customer]:
    return [_to_domain(item) for item in items]


class CustomerRepository:
    """Customer table data manipulation"""

    def insert_customer(self, **fields) -> Customer:
        """Inserts a new customer."""

        session = get_session()
        try:
            with session:
                customer = CustomerModel(**fields)
                session.add(customer)
                session.commit()
                session.refresh(customer)
                return _to_domain(customer)
        finally:
            session.close()

    def get_customers(
        self,
        search: Optional[str] = None,
        active_only: bool = False,
    ) -> List[Customer]:
        """Returns customers ordered by name, optionally filtered."""

        session = get_session()
        try:
            with session:
                sql = select(CustomerModel)
                if active_only:
                    sql = sql.where(CustomerModel.active == True)  # noqa: E712
                sql = sql.order_by(CustomerModel.name)
                all_customers = [_to_domain(c) for c in session.exec(sql).all()]
        finally:
            session.close()

        if search:
            term = strip_accents(search).lower()
            all_customers = [
                c
                for c in all_customers
                if term in strip_accents(c.name or "").lower()
                or term in strip_accents(c.cpf_cnpj or "").lower()
                or term in strip_accents(c.phone or "").lower()
            ]
        return all_customers

    def get_customer(self, customer_id: int) -> Optional[Customer]:
        """Returns a customer by its id."""

        session = get_session()
        try:
            with session:
                c = session.get(CustomerModel, customer_id)
                return _to_domain(c) if c else None
        finally:
            session.close()

    def get_customer_by_cpf_cnpj(self, cpf_cnpj: str) -> Optional[Customer]:
        """Returns a customer by CPF/CNPJ."""

        session = get_session()
        try:
            with session:
                sql = select(CustomerModel).where(CustomerModel.cpf_cnpj == cpf_cnpj)
                c = session.exec(sql).first()
                return _to_domain(c) if c else None
        finally:
            session.close()

    def update_customer(self, customer_id: int, **fields) -> Optional[Customer]:
        """Updates the fields of an existing customer."""

        session = get_session()
        try:
            with session:
                c = session.get(CustomerModel, customer_id)
                if not c:
                    return None
                for key, value in fields.items():
                    setattr(c, key, value)
                session.add(c)
                session.commit()
                session.refresh(c)
                return _to_domain(c)
        finally:
            session.close()

    def delete_customer(self, customer_id: int) -> bool:
        """Deletes a customer by its id."""

        session = get_session()
        try:
            with session:
                c = session.get(CustomerModel, customer_id)
                if not c:
                    return False
                session.delete(c)
                session.commit()
                return True
        finally:
            session.close()

    def toggle_active(self, customer_id: int) -> Optional[Customer]:
        """Toggles the active status of a customer."""

        session = get_session()
        try:
            with session:
                c = session.get(CustomerModel, customer_id)
                if not c:
                    return None
                c.active = not c.active
                session.add(c)
                session.commit()
                session.refresh(c)
                return _to_domain(c)
        finally:
            session.close()
