"""Model for repository to Bill"""

from typing import List
from datetime import datetime
from sqlmodel import select, create_engine
from billflux.errors import DefaultError
from billflux.infra.config.database import get_session
from billflux.infra.entities.bills import Bill as BillModel
from billflux.domain.models.bills import Bill


class BillRepository:
    """Bill table data manipulation"""

    def __init__(self, database_url: str):

        self.database_url = database_url

    def __session(self):

        engine = create_engine(self.database_url)
        return get_session(engine)

    def insert_bill(
        self,
        status: bool = False,
        due_date: datetime = None,
        value: float = None,
        reference: str = None,
        suplyer: str = None,
        bill_type: str = None,
        days: int = None,
        payday: datetime = None,
        value_from_payment: int = None,
        bar_code: int = None,
        obs: str = None,
        date_from_add: datetime = datetime.now(),
        user_id: int = None,
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

        with self.__session() as session:

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
                user_id=user_id,
            )

            session.add(bill)
            session.commit()
            session.refresh(bill)

            return Bill(**dict(bill))

    def get_bills(self, user_id: int = None) -> List[Bill]:
        """
        Performs a search for all Bills registered in the system.
        :param user_id: ID from user.
        :return: A list with all Bills and their data.
        """

        with self.__session() as session:

            sql = session.exec(
                select(BillModel).where(BillModel.user_id == user_id)
            ).all()

        return [Bill(**dict(bill)) for bill in sql] if sql else []

    def update_bill(
        self,
        bill_id: int,
        status: bool = None,
        due_date: datetime = None,
        value: float = None,
        reference: str = None,
        suplyer: str = None,
        bill_type: str = None,
        payday: datetime = None,
        value_from_payment: int = None,
        bar_code: int = None,
        obs: str = None,
    ) -> Bill:
        """
        Update a bill from Bill table.
        :param bill_id: ID from bill to be updated.
        :param status: Status from bill: pay or not.
        :param due_date: Due date from bill.
        :param value: Value from bill.
        :param reference: Reference from bill.
        :param suplyer: Possible bill supplier.
        :param bill_type: Type from bill.
        :param payday: Bill payment day.
        :param value_from_payment: Amount paid.
        :param bar_code: Bar code from bill.
        :param obs: Optional Observation.
        :return: The Updated Bill.
        """

        with self.__session() as session:

            bill = session.exec(
                select(BillModel).where(BillModel.id == bill_id)
            ).one_or_none()

            if not bill:

                raise DefaultError(message="Bill not found!", type_error=404)

            if status is not None:
                bill.status = status
            if due_date is not None:
                bill.due_date = due_date
            if value is not None:
                bill.value = value
            if reference is not None:
                bill.reference = reference
            if suplyer is not None:
                bill.suplyer = suplyer
            if bill_type is not None:
                bill.bill_type = bill_type
            if payday is not None:
                bill.payday = payday
            if value_from_payment is not None:
                bill.value_from_payment = value_from_payment
            if bar_code is not None:
                bill.bar_code = bar_code
            if obs is not None:
                bill.obs = obs

            session.commit()
            session.refresh(bill)

            return Bill(**dict(bill))

    def delete_bill(self, bill_id: int) -> Bill:
        """
        Deletes a bill from the database.
        :param id: Id from bill to delete.
        :return: The deleted Bill.
        """

        with self.__session() as session:

            bill = session.exec(
                select(BillModel).where(BillModel.id == bill_id)
            ).one_or_none()

            if not bill:

                raise DefaultError(message="Bill not found!", type_error=404)

            session.delete(bill)
            session.commit()

            return Bill(**dict(bill))
