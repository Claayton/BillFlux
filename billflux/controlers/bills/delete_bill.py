"""File to instantiate the blueprint for delete_bill"""

from flask.blueprints import Blueprint
from flask import jsonify
from billflux.infra.repository.bills_repository import BillRepository
from billflux.config import settings


bp = Blueprint("bp_delete_bill", __name__)

database_url = settings["development"].DATABASE_URL


@bp.route("/delete_bill/<int:bill_id>", methods=["DELETE"])
def bills(bill_id):
    """Mount bills route, and delete one bill in the table"""

    bills_repository = BillRepository(database_url)
    delete_bill = bills_repository.delete_bill(bill_id=bill_id)

    if delete_bill:
        return jsonify({"message": "Item excluído com sucesso!"}), 200
    else:
        return jsonify({"message": "Erro ao excluir o item."}), 500
