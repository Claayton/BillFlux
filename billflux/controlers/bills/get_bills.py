"""File to instantiate the blueprint for the bills page"""

from flask.blueprints import Blueprint
from flask.templating import render_template
from flask_login.utils import login_required, current_user
from billflux.infra.repository.bills_repository import BillRepository
from billflux.config import settings


bp = Blueprint("bp_get_bills", __name__)

database_url = settings["development"].DATABASE_URL


@bp.route("/bills/", methods=["GET", "POST"])
@bp.route("/bills", methods=["GET", "POST"])
@login_required
def bills():
    """Mount bills route, and list all bills in the table"""

    bills_repository = BillRepository(database_url)
    list_bills = bills_repository.get_bills(user_id=current_user.id)

    return render_template("bills.html", bills_list=list_bills)
