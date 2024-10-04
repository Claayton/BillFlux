"""File to instantiate the blueprint for the bills page"""

from datetime import datetime
from decimal import Decimal
from flask.blueprints import Blueprint
from flask.templating import render_template
from flask_login.utils import login_required, current_user
from billflux.domain.models.bills import Bill
from billflux.config import settings
from billflux.infra.repository.bills_repository import BillRepository


bp = Blueprint("bp_get_bills", __name__)

database_url = settings["development"].DATABASE_URL


@bp.route("/bills/", methods=["GET", "POST"])
@bp.route("/bills", methods=["GET", "POST"])
@login_required
def bills():
    """Mount bills route, and list all bills in the table"""

    bills_repository = BillRepository(database_url)
    list_bills = bills_repository.get_bills(user_id=current_user.id)

    formated_list_bills = []

    for bill in list_bills:

        formated_bill = Bill(
            id=bill.id,
            status=bill.status,
            due_date=bill.due_date.strftime("%d/%m/%Y"),
            value=bill.value,
            reference=bill.reference,
            suplyer=bill.suplyer,
            bill_type=bill.bill_type,
            days=(bill.due_date.date() - datetime.now().date()).days,
            payday=bill.payday if bill.payday is not None else " ",
            value_from_payment=(
                bill.value_from_payment if bill.value_from_payment is not None else " "
            ),
            bar_code=Decimal(bill.bar_code),
            obs=bill.obs,
            date_from_add=bill.date_from_add.strftime("%d/%m/%Y"),
            user_id=bill.user_id,
        )
        formated_list_bills.append(formated_bill)

    return render_template("bills.html", bills_list=formated_list_bills)
