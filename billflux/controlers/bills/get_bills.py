"""File to instantiate the blueprint for the bills page"""

from flask.blueprints import Blueprint
from flask.templating import render_template
from billflux.infra.repository.bill_repository import BillRepository
from billflux.config import settings


bp = Blueprint("bp_get_bills", __name__)

database_url = settings["development"].DATABASE_URL


@bp.route("/bills/", methods=["GET", "POST"])
@bp.route("/bills", methods=["GET", "POST"])
def bills():
    """Mount bills route, and list all bills in the table"""

    bills_repository = BillRepository(database_url)
    list_bills = bills_repository.get_bills()

    return render_template("bills.html", bills_list=list_bills)
