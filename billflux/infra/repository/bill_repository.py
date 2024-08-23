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
        status: bool = False,
        due_date: datetime = None,
        value: int = None,
        reference: str = None,
        suplyer: str = None, 
        bill_type: str = None,
        days: int = None,
        payday: datetime = None,
        value_from_payment: int = None,
        bar_code: int = None,
        obs: str = None,
        date_from_add: datetime = datetime.now(),
    ) -> Bill:
        """
        Inserts a new bill into the Bill table.
        :param value: Value from bill.
        :param reference: Reference from bill.
        :param suplyer: Possible bill supplier.
        :param bill_type: Type from bill.
        :param days: Days to pay the bill or days late.
        :param payday: Bill payment day.
        :param value_from_payment: Amount paid.
        :param bar_code: Bar code from bill.
        :param obs: Optional Observation.
        :param date_from_add: Date the bill was added.
        :return: The Registerer Bill.
        """

        with self.__session as session:

            bill = BillModel(
                status=status,
                due_date=due_date,
                value=value,
                reference=reference,
                suplyer=suplyer,
                bill_type=bill_type,
                days=days,
                payday=payday,
                value_from_payment=value_from_payment,
                bar_code=bar_code,
                obs=obs,
                date_from_add=date_from_add,
            )

            session.add(bill)
            session.commit()
            session.refresh(bill)

            return Bill(**dict(bill))

    def get_bills(self) -> List[Bill]:
        """
        Performs a search for all Bills registered in the system.
        :return: A list with all Bills and their data.
        """

        with self.__session as session:

            sql = select(BillModel)

            return list(session.exec(sql))
 