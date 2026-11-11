"""Module for repository to FiscalDocument (NFC-e do PDV)"""

from datetime import datetime
from typing import Iterable, List, Optional

from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from billflux.domain.models.fiscal_documents import FiscalDocument
from billflux.infra.config.database import get_session
from billflux.infra.entities.fiscal_document import (
    FiscalDocument as FiscalDocumentModel,
)

MUTABLE_FIELDS = frozenset(FiscalDocument._fields) - {"id", "order_id", "created_at"}


def _to_domain(model: FiscalDocumentModel) -> FiscalDocument:
    return FiscalDocument(**dict(model))


class FiscalDocumentRepository:
    """FiscalDocument table data manipulation"""

    def create_pending(
        self, order_id: int, provider: str, environment: str
    ) -> FiscalDocument:
        """Cria (ou devolve) a nota pendente de uma venda."""

        session = get_session()
        try:
            with session:
                existing = session.exec(
                    select(FiscalDocumentModel).where(
                        FiscalDocumentModel.order_id == order_id
                    )
                ).first()
                if existing:
                    return _to_domain(existing)

                model = FiscalDocumentModel(
                    order_id=order_id,
                    provider=provider,
                    environment=environment,
                    status="pendente",
                )
                session.add(model)
                try:
                    session.commit()
                except IntegrityError:
                    # Duas requisições simultâneas: a outra criou primeiro.
                    session.rollback()
                    model = session.exec(
                        select(FiscalDocumentModel).where(
                            FiscalDocumentModel.order_id == order_id
                        )
                    ).first()
                    return _to_domain(model)
                session.refresh(model)
                return _to_domain(model)
        finally:
            session.close()

    def get(self, document_id: int) -> Optional[FiscalDocument]:
        session = get_session()
        try:
            with session:
                model = session.get(FiscalDocumentModel, document_id)
                return _to_domain(model) if model else None
        finally:
            session.close()

    def get_by_order(self, order_id: int) -> Optional[FiscalDocument]:
        session = get_session()
        try:
            with session:
                model = session.exec(
                    select(FiscalDocumentModel).where(
                        FiscalDocumentModel.order_id == order_id
                    )
                ).first()
                return _to_domain(model) if model else None
        finally:
            session.close()

    def get_by_orders(self, order_ids: Iterable[int]) -> dict:
        """Notas de várias vendas de uma vez (chave = order_id)."""

        ids = [int(order_id) for order_id in order_ids]
        if not ids:
            return {}
        session = get_session()
        try:
            with session:
                models = session.exec(
                    select(FiscalDocumentModel).where(
                        FiscalDocumentModel.order_id.in_(ids)
                    )
                ).all()
                return {model.order_id: _to_domain(model) for model in models}
        finally:
            session.close()

    def list_by_status(self, statuses: Iterable[str]) -> List[FiscalDocument]:
        statuses = list(statuses)
        if not statuses:
            return []
        session = get_session()
        try:
            with session:
                models = session.exec(
                    select(FiscalDocumentModel)
                    .where(FiscalDocumentModel.status.in_(statuses))
                    .order_by(FiscalDocumentModel.created_at, FiscalDocumentModel.id)
                ).all()
                return [_to_domain(model) for model in models]
        finally:
            session.close()

    def list_all(self) -> List[FiscalDocument]:
        session = get_session()
        try:
            with session:
                models = session.exec(
                    select(FiscalDocumentModel).order_by(
                        FiscalDocumentModel.created_at.desc(),
                        FiscalDocumentModel.id.desc(),
                    )
                ).all()
                return [_to_domain(model) for model in models]
        finally:
            session.close()

    def update(self, document_id: int, **fields) -> Optional[FiscalDocument]:
        """Atualiza apenas campos conhecidos da nota."""

        session = get_session()
        try:
            with session:
                model = session.get(FiscalDocumentModel, document_id)
                if not model:
                    return None
                for key, value in fields.items():
                    if key in MUTABLE_FIELDS:
                        setattr(model, key, value)
                model.updated_at = datetime.now()
                session.add(model)
                session.commit()
                session.refresh(model)
                return _to_domain(model)
        finally:
            session.close()

    def delete(self, document_id: int) -> bool:
        session = get_session()
        try:
            with session:
                model = session.get(FiscalDocumentModel, document_id)
                if not model:
                    return False
                session.delete(model)
                session.commit()
                return True
        finally:
            session.close()
