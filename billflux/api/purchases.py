"""Endpoints de compras (purchase orders) da API JSON."""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import request

from billflux.api import bp, api_error, api_login_required, api_response, br_to_decimal
from billflux.api.nfe_parser import parse_nfe_xml
from billflux.infra.repository.purchase_repository import PurchaseRepository
from billflux.infra.repository.supplier_repository import SupplierRepository


def _serialize(po):
    return {
        "id": po.id,
        "nf_number": po.nf_number or "",
        "nf_serie": po.nf_serie or "",
        "nf_chave": po.nf_chave or "",
        "nf_modelo": po.nf_modelo or "",
        "supplier_id": po.supplier_id,
        "supplier_name": po.supplier_name or "",
        "total": str(po.total),
        "freight": str(po.freight),
        "discount": str(po.discount),
        "net_total": str(po.net_total),
        "status": po.status,
        "bill_id": po.bill_id,
        "due_date": po.due_date.isoformat() if po.due_date else None,
        "obs": po.obs or "",
        "created_at": po.created_at.isoformat() if po.created_at else None,
    }


def _serialize_item(item):
    return {
        "id": item.id,
        "purchase_id": item.purchase_id,
        "product_id": item.product_id,
        "product_name": item.product_name or "",
        "quantity": item.quantity,
        "unit_cost": str(item.unit_cost),
        "total": str(item.total),
        "barcode": item.barcode or "",
        "unit_com": item.unit_com or "",
    }


def _purchases_payload(search=None, supplier_id=None, status=None):
    repository = PurchaseRepository()
    purchases = repository.get_purchases(
        search=search,
        supplier_id=supplier_id,
        status=status,
    )
    return {"purchases": [_serialize(p) for p in purchases]}


@bp.route("/purchases")
@api_login_required
def purchases_list():
    repository = PurchaseRepository()
    search = request.args.get("search", "").strip() or None
    supplier_id = request.args.get("supplier_id", type=int) or None
    status = request.args.get("status", "").strip() or None
    purchases = repository.get_purchases(
        search=search,
        supplier_id=supplier_id,
        status=status,
    )
    return api_response({"purchases": [_serialize(p) for p in purchases]})


@bp.route("/purchases", methods=["POST"])
@api_login_required
def purchases_create():
    data = request.get_json(silent=True) or {}
    items_data = data.get("items", [])
    repository = PurchaseRepository()

    total = Decimal("0")
    parsed_items = []
    for item in items_data:
        qty = int(item.get("quantity", 1))
        cost = br_to_decimal(item.get("unit_cost")) or Decimal("0")
        line_total = Decimal(str(qty)) * cost
        parsed_items.append(
            {
                "product_id": item.get("product_id"),
                "quantity": qty,
                "unit_cost": cost,
                "total": line_total,
                "barcode": (item.get("barcode") or "").strip() or None,
                "product_name": (item.get("product_name") or "").strip() or None,
            }
        )
        total += line_total

    freight = br_to_decimal(data.get("freight")) or Decimal("0")
    discount = br_to_decimal(data.get("discount")) or Decimal("0")
    net_total = total + freight - discount

    due_date = None
    if data.get("due_date"):
        try:
            due_date = datetime.fromisoformat(data["due_date"])
        except (ValueError, TypeError):
            pass

    po = repository.insert_purchase(
        supplier_id=data.get("supplier_id"),
        nf_number=(data.get("nf_number") or "").strip() or None,
        nf_serie=(data.get("nf_serie") or "").strip() or None,
        nf_chave=(data.get("nf_chave") or "").strip() or None,
        nf_modelo=(data.get("nf_modelo") or "").strip() or None,
        total=total,
        freight=freight,
        discount=discount,
        net_total=net_total,
        status="rascunho",
        due_date=due_date,
        obs=(data.get("obs") or "").strip() or None,
        items=parsed_items,
    )
    return api_response({"purchase": _serialize(po)}, status=201)


@bp.route("/purchases/<int:purchase_id>")
@api_login_required
def purchases_detail(purchase_id):
    repository = PurchaseRepository()
    po = repository.get_purchase(purchase_id)
    if not po:
        return api_error("Compra não encontrada.", 404)
    items = repository.get_purchase_items(purchase_id)
    return api_response(
        {
            "purchase": _serialize(po),
            "items": [_serialize_item(i) for i in items],
        }
    )


@bp.route("/purchases/<int:purchase_id>", methods=["PUT"])
@api_login_required
def purchases_update(purchase_id):
    repository = PurchaseRepository()
    po = repository.get_purchase(purchase_id)
    if not po:
        return api_error("Compra não encontrada.", 404)
    if po.status != "rascunho":
        return api_error("Só é possível editar compras em rascunho.", 400)

    data = request.get_json(silent=True) or {}
    items_data = data.get("items")
    total = po.total
    if items_data is not None:
        repository.delete_purchase(purchase_id)
        new_items = []
        total = Decimal("0")
        for item in items_data:
            qty = int(item.get("quantity", 1))
            cost = br_to_decimal(item.get("unit_cost")) or Decimal("0")
            line_total = Decimal(str(qty)) * cost
            new_items.append(
                {
                    "product_id": item.get("product_id"),
                    "quantity": qty,
                    "unit_cost": cost,
                    "total": line_total,
                    "barcode": (item.get("barcode") or "").strip() or None,
                    "product_name": (item.get("product_name") or "").strip() or None,
                }
            )
            total += line_total
        freight = br_to_decimal(data.get("freight")) or Decimal("0")
        discount = br_to_decimal(data.get("discount")) or Decimal("0")
        net_total = total + freight - discount
        due_date = None
        if data.get("due_date"):
            try:
                due_date = datetime.fromisoformat(data["due_date"])
            except (ValueError, TypeError):
                pass
        repository.insert_purchase(
            supplier_id=data.get("supplier_id", po.supplier_id),
            nf_number=(data.get("nf_number") or po.nf_number or "").strip() or None,
            nf_serie=(data.get("nf_serie") or po.nf_serie or "").strip() or None,
            nf_chave=(data.get("nf_chave") or po.nf_chave or "").strip() or None,
            nf_modelo=(data.get("nf_modelo") or po.nf_modelo or "").strip() or None,
            total=total,
            freight=freight,
            discount=discount,
            net_total=net_total,
            status="rascunho",
            due_date=due_date,
            obs=(data.get("obs") or po.obs or "").strip() or None,
            items=new_items,
        )
        po = repository.get_purchase(purchase_id)
        return api_response({"purchase": _serialize(po)})

    fields = {}
    if "supplier_id" in data:
        fields["supplier_id"] = data["supplier_id"]
    if "nf_number" in data:
        fields["nf_number"] = (data["nf_number"] or "").strip() or None
    if "nf_serie" in data:
        fields["nf_serie"] = (data["nf_serie"] or "").strip() or None
    if "nf_chave" in data:
        fields["nf_chave"] = (data["nf_chave"] or "").strip() or None
    if "nf_modelo" in data:
        fields["nf_modelo"] = (data["nf_modelo"] or "").strip() or None
    if "freight" in data:
        fields["freight"] = br_to_decimal(data.get("freight")) or Decimal("0")
    if "discount" in data:
        fields["discount"] = br_to_decimal(data.get("discount")) or Decimal("0")
    if "due_date" in data:
        try:
            fields["due_date"] = datetime.fromisoformat(data["due_date"])
        except (ValueError, TypeError):
            fields["due_date"] = None
    if "obs" in data:
        fields["obs"] = (data["obs"] or "").strip() or None

    if "freight" in fields or "discount" in fields:
        f = fields.get("freight", po.freight)
        d = fields.get("discount", po.discount)
        fields["net_total"] = po.total + f - d

    repository.update_purchase(purchase_id, **fields)
    po = repository.get_purchase(purchase_id)
    return api_response({"purchase": _serialize(po)})


@bp.route("/purchases/<int:purchase_id>", methods=["DELETE"])
@api_login_required
def purchases_delete(purchase_id):
    repository = PurchaseRepository()
    po = repository.get_purchase(purchase_id)
    if not po:
        return api_error("Compra não encontrada.", 404)
    if po.status != "rascunho":
        return api_error("Só é possível excluir compras em rascunho.", 400)
    repository.delete_purchase(purchase_id)
    return api_response(_purchases_payload())


@bp.route("/purchases/<int:purchase_id>/confirm", methods=["POST"])
@api_login_required
def purchases_confirm(purchase_id):
    data = request.get_json(silent=True) or {}
    repository = PurchaseRepository()
    po = repository.get_purchase(purchase_id)
    if not po:
        return api_error("Compra não encontrada.", 404)
    if po.status != "rascunho":
        return api_error("Compra já foi processada.", 400)
    due_date = None
    if data.get("due_date"):
        try:
            due_date = datetime.fromisoformat(data["due_date"])
        except (ValueError, TypeError):
            pass
    result = repository.confirm_purchase(
        purchase_id,
        due_date=due_date,
        create_bill=data.get("create_bill", True),
        account_id=data.get("account_id"),
    )
    if not result:
        return api_error("Falha ao confirmar compra.", 400)
    return api_response({"purchase": _serialize(result)})


@bp.route("/purchases/<int:purchase_id>/cancel", methods=["POST"])
@api_login_required
def purchases_cancel(purchase_id):
    repository = PurchaseRepository()
    po = repository.get_purchase(purchase_id)
    if not po:
        return api_error("Compra não encontrada.", 404)
    if po.status != "confirmada":
        return api_error("Só é possível cancelar compras confirmadas.", 400)
    result = repository.cancel_purchase(purchase_id)
    if not result:
        return api_error("Falha ao cancelar compra.", 400)
    return api_response({"purchase": _serialize(result)})


@bp.route("/purchases/nfe-import", methods=["POST"])
@api_login_required
def purchases_nfe_import():
    data = request.get_json(silent=True) or {}
    xml_content = data.get("xml")
    if not xml_content:
        return api_error("Nenhum conteúdo XML enviado.", 400)

    parsed = parse_nfe_xml(xml_content)
    if not parsed:
        return api_error("Não foi possível processar o XML da NF-e.", 400)

    repository = PurchaseRepository()
    if parsed.get("nf_chave"):
        existing = repository.get_purchase_by_nf_chave(parsed["nf_chave"])
        if existing:
            return api_response(
                {
                    "duplicate": True,
                    "purchase": _serialize(existing),
                }
            )

    supplier_id = None
    cnpj = parsed.get("supplier_cnpj")
    if cnpj:
        sr = SupplierRepository()
        supplier = sr.get_supplier_by_cnpj(cnpj)
        if supplier:
            supplier_id = supplier.id

    repository = PurchaseRepository()
    total = parsed["total"]
    freight = parsed["freight"]
    net_total = total + freight

    po = repository.insert_purchase(
        supplier_id=supplier_id,
        nf_number=parsed.get("nf_number"),
        nf_serie=parsed.get("nf_serie"),
        nf_chave=parsed.get("nf_chave"),
        nf_modelo=parsed.get("nf_modelo"),
        total=total,
        freight=freight,
        discount=Decimal("0"),
        net_total=net_total,
        status="rascunho",
        items=parsed.get("items", []),
    )
    return api_response(
        {
            "duplicate": False,
            "purchase": _serialize(po),
        },
        status=201,
    )
