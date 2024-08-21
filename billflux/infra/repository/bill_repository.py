"""Model for repository to Bill"""

from typing import List
from datetime import datetime
from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.bill import Bill as BillModel
from billflux.domain.models.bills import Bill


class BillRepository:
    """Bill table data manipulation"""

    def __init__(self) -> None:
        self.__session = get_session()

    def insert_bill(
        self,
        value: int = None,
        reference: str = None,
        suplyer: str = None,
        bill_type: str = None,
        days: int = None,
        payday: datetime = None,
        value_from_payment: int = None,
        bar_code: int = None,
        obs: str = None,
        date_from_add: datetime = datetime.now,
    ) -> Bill:

        with self.__session as session:

            bill = BillModel(
                value=value,
                reference=reference,
                suplyer=suplyer,
                bill_type=bill_type,
                days=days,
                payday=payday,
                value_from_payment=value_from_payment,
                bar_code=bar_code,
                obs=obs,
            )
            session.add(bill)
            session.commit()
            session.refresh(bill)
            print()
            print()
            print(Bill)
            print()
            print(bill)

            return Bill(**dict(bill))

    def get_bills(self) -> List[Bill]:

        with self.__session as session:
            sql = select(BillModel)
            return list(session.exec(sql))
