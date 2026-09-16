"""API for purchase schedule — daily suggestions and product-supplier CRUD."""

from datetime import date, timedelta
from decimal import Decimal

from flask import request
from sqlmodel import select, func

from billflux.api import bp, api_login_required, api_response, api_error
from billflux.infra.config.database import get_session
from billflux.infra.entities.product import Product as ProductModel
from billflux.infra.entities.order import Order as OrderModel
from billflux.infra.entities.order_item import OrderItem as OrderItemModel
from billflux.infra.entities.supplier import Supplier as SupplierModel
from billflux.infra.entities.purchase_order import PurchaseOrder as PurchaseOrderModel
from billflux.infra.entities.purchase_item import PurchaseItem as PurchaseItemModel
from billflux.infra.repository.product_supplier_repository import (
    ProductSupplierRepository,
)

DAY_NAMES = [
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
]


def _serialize_link(ps):
    return {
        "id": ps.id,
        "product_id": ps.product_id,
        "supplier_id": ps.supplier_id,
        "supplier_name": ps.supplier_name,
        "product_name": ps.product_name,
        "delivery_day": ps.delivery_day,
        "lead_time": ps.lead_time,
        "is_primary": ps.is_primary,
        "frequency": ps.frequency,
        "week_parity": ps.week_parity,
    }


# ── CRUD de fornecedores por produto ──────────────────────────────


@bp.route("/products/<int:product_id>/suppliers")
@api_login_required
def product_suppliers(product_id):
    repo = ProductSupplierRepository()
    links = repo.get_suppliers_for_product(product_id)
    return api_response({"links": [_serialize_link(l) for l in links]})


@bp.route("/products/<int:product_id>/suppliers", methods=["POST"])
@api_login_required
def add_product_supplier(product_id):
    data = request.get_json(silent=True) or {}
    supplier_id = data.get("supplier_id")
    delivery_day = data.get("delivery_day")
    lead_time = data.get("lead_time", 1)
    is_primary = data.get("is_primary", False)
    frequency = data.get("frequency", "semanal")
    week_parity = int(data.get("week_parity", 0))

    if supplier_id is None or delivery_day is None:
        return api_error("supplier_id e delivery_day sao obrigatorios.", 400)
    if not (0 <= int(delivery_day) <= 6):
        return api_error("delivery_day deve ser 0-6 (dom-sab).", 400)
    if frequency not in ("semanal", "quinzenal", "mensal"):
        return api_error("frequency deve ser semanal, quinzenal ou mensal.", 400)

    repo = ProductSupplierRepository()
    link = repo.upsert(
        product_id=product_id,
        supplier_id=int(supplier_id),
        delivery_day=int(delivery_day),
        lead_time=int(lead_time),
        is_primary=bool(is_primary),
        frequency=frequency,
        week_parity=week_parity,
    )
    return api_response({"link": _serialize_link(link)}, status=201)


@bp.route("/product-suppliers/<int:link_id>", methods=["PUT"])
@api_login_required
def update_product_supplier(link_id):
    data = request.get_json(silent=True) or {}
    session = get_session()
    try:
        with session:
            from billflux.infra.entities.product_supplier import (
                ProductSupplier as ProductSupplierModel,
            )

            ps = session.get(ProductSupplierModel, link_id)
            if not ps:
                return api_error("Vinculo nao encontrado.", 404)
            if "delivery_day" in data:
                ps.delivery_day = int(data["delivery_day"])
            if "lead_time" in data:
                ps.lead_time = int(data["lead_time"])
            if "is_primary" in data:
                if data["is_primary"]:
                    stmt = select(ProductSupplierModel).where(
                        ProductSupplierModel.product_id == ps.product_id,
                        ProductSupplierModel.is_primary == True,
                        ProductSupplierModel.id != link_id,
                    )
                    for old in session.exec(stmt).all():
                        old.is_primary = False
                        session.add(old)
                ps.is_primary = bool(data["is_primary"])
            if "frequency" in data:
                ps.frequency = data["frequency"]
            if "week_parity" in data:
                ps.week_parity = int(data["week_parity"])
            session.add(ps)
            session.commit()
            session.refresh(ps)
            repo = ProductSupplierRepository()
            link = repo.get_by_product_and_supplier(ps.product_id, ps.supplier_id)
            return api_response({"link": _serialize_link(link)})
    finally:
        session.close()


@bp.route("/product-suppliers/<int:link_id>", methods=["DELETE"])
@api_login_required
def delete_product_supplier(link_id):
    repo = ProductSupplierRepository()
    if repo.delete(link_id):
        return api_response({"ok": True})
    return api_error("Vinculo nao encontrado.", 404)


# ── Cálculo de agenda ─────────────────────────────────────────────


def _avg_daily_sales(product_id: int, days: int = 28) -> Decimal:
    session = get_session()
    try:
        with session:
            cutoff = date.today() - timedelta(days=days)
            stmt = (
                select(func.coalesce(func.sum(OrderItemModel.quantity), 0))
                .join(OrderModel, OrderItemModel.order_id == OrderModel.id)
                .where(
                    OrderItemModel.product_id == product_id,
                    OrderModel.cancelled == False,
                    OrderModel.created_at >= str(cutoff),
                )
            )
            total = session.exec(stmt).one()
            return Decimal(str(total)) / Decimal(str(days))
    finally:
        session.close()


def _is_delivery_active_today(link) -> bool:
    """Verifica se um vínculo deve entregar hoje, baseado na frequência."""
    from datetime import date

    freq = getattr(link, "frequency", "semanal") or "semanal"
    parity = getattr(link, "week_parity", 0) or 0

    if freq == "semanal":
        return True

    today = date.today()

    if freq == "quinzenal":
        iso_week = today.isocalendar()[1]
        return (iso_week % 2) == parity

    if freq == "mensal":
        day_of_month = today.day
        if day_of_month <= 7:
            return parity == 0
        elif day_of_month <= 14:
            return parity == 1
        elif day_of_month <= 21:
            return parity == 2
        else:
            return parity == 3

    return True


def _build_suggestions(delivery_day: int) -> list:
    repo = ProductSupplierRepository()
    links = repo.get_all_for_day(delivery_day)

    by_supplier = {}
    for link in links:
        if not _is_delivery_active_today(link):
            continue
        session = get_session()
        try:
            with session:
                product = session.get(ProductModel, link.product_id)
                if not product or not product.active:
                    continue
                ideal = getattr(product, "ideal_stock", 0) or 0
                current = product.stock_quantity
                if ideal <= 0 or current >= ideal:
                    continue
                suggested_qty = ideal - current
                avg_daily = _avg_daily_sales(link.product_id)
                entry = {
                    "product_id": product.id,
                    "product_name": product.name,
                    "current_stock": current,
                    "ideal_stock": ideal,
                    "suggested_qty": suggested_qty,
                    "avg_daily_sales": float(avg_daily),
                }
                if link.supplier_id not in by_supplier:
                    by_supplier[link.supplier_id] = {
                        "supplier_id": link.supplier_id,
                        "supplier_name": link.supplier_name,
                        "products": [],
                    }
                by_supplier[link.supplier_id]["products"].append(entry)
        finally:
            session.close()

    return list(by_supplier.values())


@bp.route("/schedule/today")
@api_login_required
def schedule_today():
    today = date.today()
    weekday = today.weekday()
    suggestions = _build_suggestions(weekday)
    return api_response(
        {
            "date": today.isoformat(),
            "day_of_week": DAY_NAMES[weekday],
            "suggestions": suggestions,
        }
    )


@bp.route("/schedule/week")
@api_login_required
def schedule_week():
    today = date.today()
    today_weekday = today.weekday()
    week = []
    for i in range(7):
        day_date = today + timedelta(days=i - today_weekday)
        weekday = day_date.weekday()
        suggestions = _build_suggestions(weekday)
        week.append(
            {
                "date": day_date.isoformat(),
                "day_name": DAY_NAMES[weekday],
                "day_of_week": weekday,
                "is_today": day_date == today,
                "suggestions": suggestions,
                "supplier_count": len(suggestions),
                "product_count": sum(len(s["products"]) for s in suggestions),
            }
        )
    return api_response({"week": week})


@bp.route("/schedule/create-order", methods=["POST"])
@api_login_required
def create_order_from_suggestions():
    data = request.get_json(silent=True) or {}
    supplier_id = data.get("supplier_id")
    if not supplier_id:
        return api_error("supplier_id e obrigatorio.", 400)

    today = date.today()
    weekday = today.weekday()
    suggestions = _build_suggestions(weekday)

    target = None
    for s in suggestions:
        if s["supplier_id"] == int(supplier_id):
            target = s
            break

    if not target:
        return api_error("Nenhuma sugestao encontrada para este fornecedor hoje.", 404)

    session = get_session()
    try:
        with session:
            po = PurchaseOrderModel(
                supplier_id=int(supplier_id),
                status="rascunho",
                total=Decimal("0"),
                freight=Decimal("0"),
                discount=Decimal("0"),
                net_total=Decimal("0"),
                obs=f"Gerado automaticamente em {today.isoformat()}",
            )
            session.add(po)
            session.flush()

            total = Decimal("0")
            for p in target["products"]:
                qty = p["suggested_qty"]
                cost = Decimal("0")
                product = session.get(ProductModel, p["product_id"])
                if product:
                    cost = product.cost
                item_total = cost * qty
                total += item_total
                session.add(
                    PurchaseItemModel(
                        purchase_id=po.id,
                        product_id=p["product_id"],
                        product_name=p["product_name"],
                        quantity=qty,
                        unit_cost=cost,
                        total=item_total,
                    )
                )

            po.total = total
            po.net_total = total
            session.add(po)
            session.commit()
            session.refresh(po)

            return api_response(
                {
                    "purchase_id": po.id,
                    "status": po.status,
                    "items_count": len(target["products"]),
                },
                status=201,
            )
    finally:
        session.close()
