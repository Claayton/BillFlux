from flask.blueprints import Blueprint
from flask.templating import render_template

bp = Blueprint("bp_tickets", __name__)


@bp.route("/tickets/", methods=["GET", "POST"])
@bp.route("/tickets", methods=["GET", "POST"])
def tasks():
    return render_template("tickets.html")
