"""Module for repository to ScheduledOrder (encargos/agenda de pedidos)"""

import json
from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.scheduled_order import (
    ScheduledOrder as ScheduledOrderModel,
)

ORDER_STATUSES = ("pendente", "confirmado", "listo", "entregado", "cancelado")


def _serialize_items(items_json: Optional[str]) -> list:
    if not items_json:
        return []
    try:
        data = json.loads(items_json)
        return data if isinstance(data, list) else []
    except (ValueError, TypeError):
        return []


def _items_json(items: Optional[list]) -> Optional[str]:
    if not items:
        return None
    return json.dumps(items, ensure_ascii=False)


class ScheduledOrderRepository:
    """ScheduledOrder table data manipulation."""

    def create_order(
        self,
        order_date: Optional[date] = None,
        order_time: Optional[str] = None,
        customer_id: Optional[int] = None,
        customer_name: Optional[str] = None,
        status: str = "pendente",
        obs: Optional[str] = None,
        items: Optional[list] = None,
        total: Optional[Decimal] = None,
    ) -> ScheduledOrderModel:
        session = get_session()
        try:
            with session:
                model = ScheduledOrderModel(
                    order_date=order_date,
                    order_time=order_time,
                    customer_id=customer_id,
                    customer_name=customer_name,
                    status=status,
                    obs=obs,
                    items=_items_json(items),
                    total=total if total is not None else Decimal("0"),
                )
                session.add(model)
                session.commit()
                session.refresh(model)
                return model
        finally:
            session.close()

    def list_orders(
        self,
        order_date: Optional[date] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[ScheduledOrderModel]:
        session = get_session()
        try:
            with session:
                sql = select(ScheduledOrderModel)
                if order_date:
                    sql = sql.where(ScheduledOrderModel.order_date == order_date)
                if status:
                    sql = sql.where(ScheduledOrderModel.status == status)
                sql = sql.order_by(
                    ScheduledOrderModel.order_date, ScheduledOrderModel.order_time
                )
                orders = session.exec(sql).all()
                if search:
                    term = search.strip().lower()
                    orders = [
                        o
                        for o in orders
                        if term in (o.customer_name or "").lower()
                        or term in (o.obs or "").lower()
                    ]
                return list(orders)
        finally:
            session.close()

    def get_order(self, order_id: int) -> Optional[ScheduledOrderModel]:
        session = get_session()
        try:
            with session:
                return session.get(ScheduledOrderModel, order_id)
        finally:
            session.close()

    def update_order(
        self,
        order_id: int,
        fields: dict,
        items: Optional[list] = None,
    ) -> Optional[ScheduledOrderModel]:
        session = get_session()
        try:
            with session:
                model = session.get(ScheduledOrderModel, order_id)
                if not model:
                    return None
                for key, value in fields.items():
                    setattr(model, key, value)
                if items is not None:
                    model.items = _items_json(items)
                    model.total = sum(Decimal(str(i.get("total") or 0)) for i in items)
                session.add(model)
                session.commit()
                session.refresh(model)
                return model
        finally:
            session.close()

    def set_status(self, order_id: int, status: str) -> Optional[ScheduledOrderModel]:
        session = get_session()
        try:
            with session:
                model = session.get(ScheduledOrderModel, order_id)
                if not model:
                    return None
                model.status = status
                session.add(model)
                session.commit()
                session.refresh(model)
                return model
        finally:
            session.close()

    def delete_order(self, order_id: int) -> bool:
        session = get_session()
        try:
            with session:
                model = session.get(ScheduledOrderModel, order_id)
                if not model:
                    return False
                session.delete(model)
                session.commit()
                return True
        finally:
            session.close()
