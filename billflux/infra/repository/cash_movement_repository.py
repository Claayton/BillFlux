"""Module for repository to CashMovement (sangria/suprimento)"""

from typing import Dict, List

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.cash_movement import CashMovement as CashMovementModel
from billflux.domain.models.cash_movements import CashMovement


def _to_domain(m: CashMovementModel) -> CashMovement:
    return CashMovement(
        id=m.id,
        cash_register_id=m.cash_register_id,
        kind=m.kind,
        amount=m.amount,
        obs=m.obs,
        created_by=m.created_by,
        created_at=m.created_at,
    )


class CashMovementRepository:
    """CashMovement table data manipulation"""

    def create(
        self,
        cash_register_id: int,
        kind: str,
        amount: float,
        created_by: str,
        obs: str | None = None,
    ) -> CashMovement:
        """Registra uma sangria ou suprimento no caixa aberto."""
        session = get_session()
        try:
            with session:
                model = CashMovementModel(
                    cash_register_id=cash_register_id,
                    kind=kind,
                    amount=amount,
                    obs=obs,
                    created_by=created_by,
                )
                session.add(model)
                session.commit()
                session.refresh(model)
                return _to_domain(model)
        finally:
            session.close()

    def list_for_register(self, cash_register_id: int) -> List[CashMovement]:
        """Movimentações de um caixa, mais recentes primeiro."""
        session = get_session()
        try:
            with session:
                rows = session.exec(
                    select(CashMovementModel)
                    .where(CashMovementModel.cash_register_id == cash_register_id)
                    .order_by(CashMovementModel.id.desc())
                ).all()
                return [_to_domain(m) for m in rows]
        finally:
            session.close()

    def totals_by_kind(self, cash_register_id: int) -> Dict[str, float]:
        """Soma por tipo: {'sangria': X, 'suprimento': Y}."""
        totals = {"sangria": 0.0, "suprimento": 0.0}
        for m in self.list_for_register(cash_register_id):
            if m.kind in totals:
                totals[m.kind] = round(totals[m.kind] + (m.amount or 0), 2)
        return totals
