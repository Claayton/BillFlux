"""Model for repository to Sale (vendas diárias)"""

from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.sale import Sale as SaleModel
from billflux.domain.models.sales import Sale


class SaleRepository:
    """Sale table data manipulation"""

    def insert_sale(
        self,
        date: date,
        total: Decimal,
        obs: Optional[str] = None,
    ) -> Sale:
        """Inserts or updates (upsert by date) the daily sale total."""

        session = get_session()
        try:
            with session:
                sale = session.exec(
                    select(SaleModel).where(SaleModel.date == date)
                ).first()
                if sale:
                    sale.total = total
                    sale.obs = obs
                    session.add(sale)
                    session.commit()
                    session.refresh(sale)
                    return Sale(**dict(sale))
                sale = SaleModel(date=date, total=total, obs=obs)
                session.add(sale)
                session.commit()
                session.refresh(sale)
                return Sale(**dict(sale))
        finally:
            session.close()

    def get_sales(self) -> List[Sale]:
        """Returns all daily sales ordered by date (newest first)."""

        session = get_session()
        try:
            with session:
                sql = select(SaleModel).order_by(SaleModel.date.desc())
                sales = session.exec(sql).all()
                return [Sale(**dict(sale)) for sale in sales]
        finally:
            session.close()

    def get_sale(self, sale_id: int) -> Optional[Sale]:
        """Returns a daily sale by its id."""

        session = get_session()
        try:
            with session:
                sale = session.get(SaleModel, sale_id)
                return Sale(**dict(sale)) if sale else None
        finally:
            session.close()

    def get_sale_by_date(self, date: date) -> Optional[Sale]:
        """Returns the daily sale of a specific date."""

        session = get_session()
        try:
            with session:
                sale = session.exec(
                    select(SaleModel).where(SaleModel.date == date)
                ).first()
                return Sale(**dict(sale)) if sale else None
        finally:
            session.close()

    def delete_sale(self, sale_id: int) -> bool:
        """Deletes a daily sale by its id."""

        session = get_session()
        try:
            with session:
                sale = session.get(SaleModel, sale_id)
                if not sale:
                    return False
                session.delete(sale)
                session.commit()
                return True
        finally:
            session.close()
