from flask.blueprints import Blueprint
from flask.templating import render_template

bp = Blueprint("bp_tickets", __name__)


@bp.route("/tickets")
def index():
    return render_template("tickets.html")
