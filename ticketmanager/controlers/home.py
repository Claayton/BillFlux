from flask.blueprints import Blueprint
from flask.templating import render_template

bp = Blueprint("bp_home", __name__)


@bp.route("/home")
@bp.route("/")
def index():
    return render_template("home.html")
