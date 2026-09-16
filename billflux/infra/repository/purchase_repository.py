"""Module for repository to PurchaseOrder (compras de produtos)"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.purchase_order import PurchaseOrder as PurchaseOrderModel
from billflux.infra.entities.purchase_item import PurchaseItem as PurchaseItemModel
from billflux.infra.entities.product import Product as ProductModel
from billflux.infra.entities.product_movement import (
    ProductMovement as ProductMovementModel,
)
from billflux.infra.entities.supplier import Supplier as SupplierModel
from billflux.infra.entities.bill import Bill as BillModel
from billflux.domain.models.purchase_orders import PurchaseOrder
from billflux.domain.models.purchase_items import PurchaseItem
from billflux.services.text_normalize import strip_accents


def _to_domain(po, supplier_name=None):
    return PurchaseOrder(
        id=po.id,
        nf_number=po.nf_number,
        nf_serie=po.nf_serie,
        nf_chave=po.nf_chave,
        nf_modelo=po.nf_modelo,
        supplier_id=po.supplier_id,
        supplier_name=supplier_name,
        total=po.total,
        freight=po.freight,
        discount=po.discount,
        net_total=po.net_total,
        status=po.status,
        bill_id=po.bill_id,
        due_date=po.due_date,
        obs=po.obs,
        created_at=po.created_at,
    )


def _item_to_domain(item):
    return PurchaseItem(
        id=item.id,
        purchase_id=item.purchase_id,
        product_id=item.product_id,
        product_name=item.product_name,
        quantity=item.quantity,
        unit_cost=item.unit_cost,
        total=item.total,
        barcode=item.barcode,
        unit_com=item.unit_com,
    )


def _resolve_supplier_name(supplier_id):
    if not supplier_id:
        return None
    session = get_session()
    try:
        supplier = session.get(SupplierModel, supplier_id)
        return supplier.name if supplier else None
    finally:
        session.close()


class PurchaseRepository:

    def insert_purchase(
        self,
        supplier_id=None,
        nf_number=None,
        nf_serie=None,
        nf_chave=None,
        nf_modelo=None,
        total=Decimal("0"),
        freight=Decimal("0"),
        discount=Decimal("0"),
        net_total=Decimal("0"),
        status="rascunho",
        bill_id=None,
        due_date=None,
        obs=None,
        items=None,
    ):
        session = get_session()
        try:
            with session:
                po = PurchaseOrderModel(
                    supplier_id=supplier_id,
                    nf_number=nf_number,
                    nf_serie=nf_serie,
                    nf_chave=nf_chave,
                    nf_modelo=nf_modelo,
                    total=total,
                    freight=freight,
                    discount=discount,
                    net_total=net_total,
                    status=status,
                    bill_id=bill_id,
                    due_date=due_date,
                    obs=obs,
                )
                session.add(po)
                session.flush()
                if items:
                    for d in items:
                        session.add(
                            PurchaseItemModel(
                                purchase_id=po.id,
                                product_id=d.get("product_id"),
                                quantity=d["quantity"],
                                unit_cost=d.get("unit_cost", Decimal("0")),
                                total=d.get("total", Decimal("0")),
                                barcode=d.get("barcode"),
                                product_name=d.get("product_name"),
                                unit_com=d.get("unit_com"),
                            )
                        )
                session.commit()
                session.refresh(po)
                return _to_domain(po, _resolve_supplier_name(po.supplier_id))
        finally:
            session.close()

    def get_purchases(self, search=None, supplier_id=None, status=None):
        session = get_session()
        try:
            with session:
                sql = select(PurchaseOrderModel).order_by(
                    PurchaseOrderModel.created_at.desc()
                )
                if supplier_id:
                    sql = sql.where(PurchaseOrderModel.supplier_id == supplier_id)
                if status:
                    sql = sql.where(PurchaseOrderModel.status == status)
                results = [
                    _to_domain(po, _resolve_supplier_name(po.supplier_id))
                    for po in session.exec(sql).all()
                ]
        finally:
            session.close()

        if search:
            term = strip_accents(search).lower()
            results = [
                p
                for p in results
                if term in strip_accents(p.nf_chave or "").lower()
                or term in strip_accents(p.nf_number or "").lower()
                or term in strip_accents(p.obs or "").lower()
            ]
        return results

    def get_purchase(self, purchase_id):
        session = get_session()
        try:
            with session:
                po = session.get(PurchaseOrderModel, purchase_id)
                if not po:
                    return None
                return _to_domain(po, _resolve_supplier_name(po.supplier_id))
        finally:
            session.close()

    def get_purchase_items(self, purchase_id):
        session = get_session()
        try:
            with session:
                sql = select(PurchaseItemModel).where(
                    PurchaseItemModel.purchase_id == purchase_id
                )
                return [_item_to_domain(i) for i in session.exec(sql).all()]
        finally:
            session.close()

    def get_purchase_by_nf_chave(self, chave):
        session = get_session()
        try:
            with session:
                po = session.exec(
                    select(PurchaseOrderModel).where(
                        PurchaseOrderModel.nf_chave == chave
                    )
                ).first()
                if not po:
                    return None
                return _to_domain(po, _resolve_supplier_name(po.supplier_id))
        finally:
            session.close()

    def confirm_purchase(
        self, purchase_id, due_date=None, create_bill=True, account_id=None
    ):
        session = get_session()
        try:
            with session:
                po = session.get(PurchaseOrderModel, purchase_id)
                if not po or po.status != "rascunho":
                    return None
                items = session.exec(
                    select(PurchaseItemModel).where(
                        PurchaseItemModel.purchase_id == purchase_id
                    )
                ).all()

                bill_id = None
                if create_bill and po.net_total > 0:
                    bill = BillModel(
                        status=False,
                        due_date=due_date,
                        value=po.net_total,
                        reference=f"Compra #{po.id}"
                        + (f" NF {po.nf_number}" if po.nf_number else ""),
                        supplier_id=po.supplier_id,
                        bill_type="compra",
                        obs=f"Compra de mercadorias #{po.id}",
                        account_id=account_id,
                        date_from_add=datetime.now(),
                    )
                    session.add(bill)
                    session.flush()
                    bill_id = bill.id
                    po.bill_id = bill_id

                for item in items:
                    if item.product_id:
                        product = session.get(ProductModel, item.product_id)
                        if product:
                            product.stock_quantity += item.quantity
                            if item.unit_cost > 0:
                                current_qty = product.stock_quantity - item.quantity
                                current_cost = product.cost or Decimal("0")
                                new_qty = item.quantity
                                new_cost = item.unit_cost
                                if current_qty > 0 and current_cost > 0:
                                    total_qty = current_qty + new_qty
                                    product.cost = (
                                        (current_qty * current_cost)
                                        + (new_qty * new_cost)
                                    ) / Decimal(str(total_qty))
                                else:
                                    product.cost = new_cost
                            session.add(product)
                            nf_ref = f" NF {po.nf_number}" if po.nf_number else ""
                            session.add(
                                ProductMovementModel(
                                    product_id=product.id,
                                    movement_type="entrada",
                                    quantity=item.quantity,
                                    obs=f"Compra #{po.id}{nf_ref}",
                                )
                            )

                po.status = "confirmada"
                session.add(po)
                session.commit()
                session.refresh(po)
                return _to_domain(po, _resolve_supplier_name(po.supplier_id))
        finally:
            session.close()

    def cancel_purchase(self, purchase_id):
        session = get_session()
        try:
            with session:
                po = session.get(PurchaseOrderModel, purchase_id)
                if not po or po.status != "confirmada":
                    return None
                items = session.exec(
                    select(PurchaseItemModel).where(
                        PurchaseItemModel.purchase_id == purchase_id
                    )
                ).all()
                for item in items:
                    if item.product_id:
                        product = session.get(ProductModel, item.product_id)
                        if product:
                            product.stock_quantity = max(
                                product.stock_quantity - item.quantity, 0
                            )
                            session.add(product)
                            session.add(
                                ProductMovementModel(
                                    product_id=product.id,
                                    movement_type="saida",
                                    quantity=-item.quantity,
                                    obs=f"Cancelamento compra #{po.id}",
                                )
                            )
                if po.bill_id:
                    bill = session.get(BillModel, po.bill_id)
                    if bill:
                        bill.obs = (
                            (bill.obs or "") + " [Cancelado via compra]"
                        ).strip()
                        session.add(bill)
                po.status = "cancelada"
                po.bill_id = None
                session.add(po)
                session.commit()
                session.refresh(po)
                return _to_domain(po, _resolve_supplier_name(po.supplier_id))
        finally:
            session.close()

    def delete_purchase(self, purchase_id):
        session = get_session()
        try:
            with session:
                po = session.get(PurchaseOrderModel, purchase_id)
                if not po or po.status != "rascunho":
                    return False
                items = session.exec(
                    select(PurchaseItemModel).where(
                        PurchaseItemModel.purchase_id == purchase_id
                    )
                ).all()
                for item in items:
                    session.delete(item)
                session.delete(po)
                session.commit()
                return True
        finally:
            session.close()

    def update_purchase(self, purchase_id, **fields):
        session = get_session()
        try:
            with session:
                po = session.get(PurchaseOrderModel, purchase_id)
                if not po or po.status != "rascunho":
                    return None
                for key, value in fields.items():
                    setattr(po, key, value)
                session.add(po)
                session.commit()
                session.refresh(po)
                return _to_domain(po, _resolve_supplier_name(po.supplier_id))
        finally:
            session.close()

    def upsert_item(
        self,
        purchase_id,
        product_id=None,
        quantity=1,
        unit_cost=Decimal("0"),
        barcode=None,
        product_name=None,
        item_id=None,
    ):
        session = get_session()
        try:
            with session:
                if item_id:
                    item = session.get(PurchaseItemModel, item_id)
                    if not item or item.purchase_id != purchase_id:
                        return None
                else:
                    item = PurchaseItemModel(purchase_id=purchase_id)
                item.product_id = product_id
                item.quantity = quantity
                item.unit_cost = unit_cost
                item.total = Decimal(str(quantity)) * unit_cost
                item.barcode = barcode
                item.product_name = product_name
                session.add(item)
                session.commit()
                session.refresh(item)
                return _item_to_domain(item)
        finally:
            session.close()

    def delete_item(self, item_id):
        session = get_session()
        try:
            with session:
                item = session.get(PurchaseItemModel, item_id)
                if not item:
                    return False
                po = session.get(PurchaseOrderModel, item.purchase_id)
                if po and po.status != "rascunho":
                    return False
                session.delete(item)
                session.commit()
                return True
        finally:
            session.close()
