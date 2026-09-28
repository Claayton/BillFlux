"""Module for repository to stock reports (movimentações e estoque baixo)"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import func, or_, and_
from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.product_movement import (
    ProductMovement as ProductMovementModel,
)
from billflux.infra.entities.product import Product as ProductModel
from billflux.domain.models.stock_movements import StockMovement
from billflux.domain.models.products import Product
from billflux.infra.repository.product_repository import _to_domains


def _start_of_day(value: datetime) -> datetime:
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


class ReportRepository:
    """Consultas de relatórios de estoque"""

    def list_movements(
        self,
        product_id: Optional[int] = None,
        movement_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[StockMovement], int]:
        """Movimentações de estoque com filtros, mais recentes primeiro.

        Retorna (página, total de registros que casam com os filtros)."""
        session = get_session()
        try:
            with session:
                conditions = []
                if product_id is not None:
                    conditions.append(ProductMovementModel.product_id == product_id)
                if movement_type:
                    conditions.append(
                        ProductMovementModel.movement_type == movement_type
                    )
                if date_from is not None:
                    conditions.append(
                        ProductMovementModel.created_at >= _start_of_day(date_from)
                    )
                if date_to is not None:
                    day_after = _start_of_day(date_to) + timedelta(days=1)
                    conditions.append(ProductMovementModel.created_at < day_after)

                count_sql = select(func.count(ProductMovementModel.id))
                rows_sql = select(
                    ProductMovementModel,
                    ProductModel.name,
                ).join(ProductModel, ProductModel.id == ProductMovementModel.product_id)
                if conditions:
                    count_sql = count_sql.where(*conditions)
                    rows_sql = rows_sql.where(*conditions)

                total = session.exec(count_sql).one()
                rows = session.exec(
                    rows_sql.order_by(
                        ProductMovementModel.created_at.desc(),
                        ProductMovementModel.id.desc(),
                    )
                    .offset(offset)
                    .limit(limit)
                ).all()

                items = [
                    StockMovement(
                        id=movement.id,
                        product_id=movement.product_id,
                        product_name=name,
                        movement_type=movement.movement_type,
                        quantity=movement.quantity,
                        obs=movement.obs,
                        created_at=movement.created_at,
                    )
                    for movement, name in rows
                ]
                return items, total
        finally:
            session.close()

    def low_stock_products(self) -> List[Product]:
        """Produtos ativos abaixo do mínimo definido ou com estoque negativo.

        Produtos sem mínimo configurado (min_stock = 0) e com estoque zerado
        não entram: ainda não passaram por controle de estoque."""
        session = get_session()
        try:
            with session:
                sql = (
                    select(ProductModel)
                    .where(
                        ProductModel.active == True,  # noqa: E712
                        or_(
                            ProductModel.stock_quantity < 0,
                            and_(
                                ProductModel.min_stock > 0,
                                ProductModel.stock_quantity <= ProductModel.min_stock,
                            ),
                        ),
                    )
                    .order_by(
                        ProductModel.stock_quantity.asc(), ProductModel.name.asc()
                    )
                )
                products = session.exec(sql).all()
                return _to_domains(list(products))
        finally:
            session.close()
