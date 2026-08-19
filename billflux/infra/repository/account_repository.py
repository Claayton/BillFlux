"""Model for repository to Account (plano de contas)"""

from typing import List, Optional

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.account import Account as AccountModel
from billflux.domain.models.accounts import Account


class AccountRepository:
    """Account table data manipulation"""

    def insert_account(
        self,
        name: str,
        type: str = "despesa",
        parent_id: Optional[int] = None,
        color: Optional[str] = None,
        active: bool = True,
    ) -> Account:
        """Inserts a new account (category) into the Account table."""

        session = get_session()
        try:
            with session:
                account = AccountModel(
                    name=name,
                    type=type,
                    parent_id=parent_id,
                    color=color,
                    active=active,
                )
                session.add(account)
                session.commit()
                session.refresh(account)
                return Account(**dict(account))
        finally:
            session.close()

    def get_accounts(self) -> List[Account]:
        """Returns all registered accounts."""

        session = get_session()
        try:
            with session:
                sql = select(AccountModel).order_by(
                    AccountModel.type, AccountModel.name
                )
                accounts = session.exec(sql).all()
                return [Account(**dict(account)) for account in accounts]
        finally:
            session.close()

    def get_account(self, account_id: int) -> Optional[Account]:
        """Returns an account by its id."""

        session = get_session()
        try:
            with session:
                account = session.get(AccountModel, account_id)
                return Account(**dict(account)) if account else None
        finally:
            session.close()

    def update_account(self, account_id: int, **fields: object) -> Optional[Account]:
        """Updates the fields of an existing account."""

        session = get_session()
        try:
            with session:
                account = session.get(AccountModel, account_id)
                if not account:
                    return None
                for key, value in fields.items():
                    setattr(account, key, value)
                session.add(account)
                session.commit()
                session.refresh(account)
                return Account(**dict(account))
        finally:
            session.close()

    def delete_account(self, account_id: int) -> bool:
        """Deletes an account by its id."""

        session = get_session()
        try:
            with session:
                account = session.get(AccountModel, account_id)
                if not account:
                    return False
                session.delete(account)
                session.commit()
                return True
        finally:
            session.close()

    def count_children(self, account_id: int) -> int:
        """Counts subcategories linked to an account."""

        session = get_session()
        try:
            with session:
                sql = select(AccountModel).where(AccountModel.parent_id == account_id)
                return len(session.exec(sql).all())
        finally:
            session.close()

    def count_bills(self, account_id: int) -> int:
        """Counts bills linked to an account."""

        from billflux.infra.entities.bill import Bill

        session = get_session()
        try:
            with session:
                sql = select(Bill).where(Bill.account_id == account_id)
                return len(session.exec(sql).all())
        finally:
            session.close()
