"""Model for repository to Bill"""

from typing import List
from datetime import datetime
from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.models import Bill as BillModel
from billflux.domain.models.bills import Bill


class BillRepository:
    """Bill table data manipulation"""

    def __init__(self) -> None:
        self.__session = get_session()

    def insert_bill(
        self,
        bar_code: int,
        suplyer: str,
        type: str,
        due_date: datetime = None,
        payday: datetime = None,
        is_paid_out: bool = None,
    ) -> Bill:

        with self.__session as session:

            bill = BillModel(bar_code=bar_code, type=type, suplyer=suplyer)

            session.add(bill)
            session.commit()
            session.refresh(bill)

            return Bill(**dict(bill))

    def get_bills(self) -> List[Bill]:

        with self.__session as session:
            sql = select(BillModel)
            return list(session.exec(sql))
