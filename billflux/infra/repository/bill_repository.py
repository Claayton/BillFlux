"""Model for repository to Bill"""

from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.bill import Bill as BillModel
from billflux.domain.models.bills import Bill


class BillRepository:
    """Bill table data manipulation"""

    def insert_bill(
        self,
        status: bool = False,
        due_date: datetime = None,
        value: Optional[Decimal] = None,
        reference: str = None,
        suplyer: str = None,
        bill_type: str = None,
        days: int = None,
        payday: datetime = None,
        value_from_payment: Optional[Decimal] = None,
        bar_code: str = None,
        pix_key: str = None,
        pix_payload: str = None,
        pix_image: str = None,
        obs: str = None,
        account_id: int = None,
        date_from_add: datetime = None,
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
        :param account_id: Category id from the chart of accounts.
        :param date_from_add: Date the bill was added.
        :return: The Registerer Bill.
        """

        session = get_session()
        try:
            with session:
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
                    pix_key=pix_key,
                    pix_payload=pix_payload,
                    pix_image=pix_image,
                    obs=obs,
                    account_id=account_id,
                    date_from_add=date_from_add or datetime.now(),
                )

                session.add(bill)
                session.commit()
                session.refresh(bill)

                return Bill(**dict(bill))
        finally:
            session.close()

    def get_bills(self) -> List[Bill]:
        """
        Performs a search for all Bills registered in the system.
        :return: A list with all Bills and their data.
        """

        session = get_session()
        try:
            with session:
                sql = select(BillModel)
                bills = session.exec(sql).all()
                return [Bill(**dict(bill)) for bill in bills]
        finally:
            session.close()

    def get_bill(self, bill_id: int) -> Optional[Bill]:
        """
        Searches a Bill by its id.
        :param bill_id: Bill id.
        :return: The Bill or None when not found.
        """

        session = get_session()
        try:
            with session:
                bill = session.get(BillModel, bill_id)
                return Bill(**dict(bill)) if bill else None
        finally:
            session.close()

    def pay_bill(self, bill_id: int) -> Optional[Bill]:
        """
        Marks a Bill as paid, recording the payment date.
        :param bill_id: Bill id.
        :return: The updated Bill or None when not found.
        """

        session = get_session()
        try:
            with session:
                bill = session.get(BillModel, bill_id)
                if not bill:
                    return None
                bill.status = True
                bill.payday = datetime.now()
                session.add(bill)
                session.commit()
                session.refresh(bill)
                return Bill(**dict(bill))
        finally:
            session.close()

    def update_bill(self, bill_id: int, **fields: object) -> Optional[Bill]:
        """
        Updates the fields of an existing Bill.
        :param bill_id: Bill id.
        :param fields: Field name/value pairs to update.
        :return: The updated Bill or None when not found.
        """

        session = get_session()
        try:
            with session:
                bill = session.get(BillModel, bill_id)
                if not bill:
                    return None
                for key, value in fields.items():
                    setattr(bill, key, value)
                session.add(bill)
                session.commit()
                session.refresh(bill)
                return Bill(**dict(bill))
        finally:
            session.close()

    def delete_bill(self, bill_id: int) -> bool:
        """
        Deletes a Bill by its id.
        :param bill_id: Bill id.
        :return: True when deleted, False when not found.
        """

        session = get_session()
        try:
            with session:
                bill = session.get(BillModel, bill_id)
                if not bill:
                    return False
                session.delete(bill)
                session.commit()
                return True
        finally:
            session.close()

    def cleanup_pix_data(self, days: int) -> int:
        """
        Removes the PIX QR image/payload of bills paid more than ``days`` ago.
        :param days: Retention period after the payment date.
        :return: Number of bills updated.
        """

        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        session = get_session()
        try:
            with session:
                bills = session.exec(
                    select(BillModel).where(
                        BillModel.status.is_(True), BillModel.payday.is_not(None)
                    )
                ).all()
                count = 0
                for bill in bills:
                    if bill.payday and bill.payday <= cutoff:
                        bill.pix_image = None
                        bill.pix_payload = None
                        session.add(bill)
                        count += 1
                session.commit()
                return count
        finally:
            session.close()
