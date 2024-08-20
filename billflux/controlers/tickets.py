from flask.blueprints import Blueprint
from flask.templating import render_template
from billflux.infra.repository.tickets_repository import TicketRepository


bp = Blueprint("bp_tickets", __name__)


@bp.route("/tickets/", methods=["GET", "POST"])
@bp.route("/tickets", methods=["GET", "POST"])
def tasks():

    ticket_repository = TicketRepository()
    tickets_list = ticket_repository.get_tickets()
    print(tickets_list)

    return render_template("tickets.html", tickets_list=tickets_list)
