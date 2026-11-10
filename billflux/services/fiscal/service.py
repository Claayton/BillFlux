"""Orquestração da emissão de NFC-e (uma nota por venda do PDV)."""

import base64
from datetime import datetime, timedelta
from typing import List, Optional

from billflux.infra.repository.customer_repository import CustomerRepository
from billflux.infra.repository.fiscal_document_repository import (
    FiscalDocumentRepository,
)
from billflux.infra.repository.order_repository import OrderRepository
from billflux.infra.repository.payment_method_repository import (
    PaymentMethodRepository,
)
from billflux.infra.repository.product_repository import ProductRepository
from billflux.services.fiscal.base import (
    PENDING_STATUSES,
    FiscalCancellationError,
    FiscalConfigError,
    FiscalError,
    FiscalProvider,
    FiscalQueryResult,
    FiscalTransportError,
    FiscalValidationError,
    STATUS_AWAITING,
    STATUS_AUTHORIZED,
    STATUS_CANCELLED,
    STATUS_DENIED,
    STATUS_PENDING,
    STATUS_REJECTED,
)
from billflux.services.fiscal.builder import build_request
from billflux.services.fiscal.config import FiscalConfig, load_config
from billflux.services.fiscal.factory import get_provider


def _retry_delay(retry_count: int) -> timedelta:
    attempt = max(retry_count, 1)
    return timedelta(minutes=min(5 * (2 ** (attempt - 1)), 60))


class FiscalService:
    """Regras de emissão, reenvio e cancelamento da NFC-e."""

    def __init__(
        self,
        provider: Optional[FiscalProvider] = None,
        config: Optional[FiscalConfig] = None,
        repository: Optional[FiscalDocumentRepository] = None,
    ):
        self._provider = provider
        self._config = config
        self.repository = repository or FiscalDocumentRepository()

    # ------------------------------------------------------------ Configuração
    @property
    def config(self) -> FiscalConfig:
        if self._config is None:
            self._config = load_config()
        return self._config

    @property
    def provider(self) -> FiscalProvider:
        if self._provider is None:
            self._provider = get_provider(self.config)
        return self._provider

    # ------------------------------------------------------------------ Emitir
    def emitir(self, order_id: int):
        """Emite (ou devolve) a nota de uma venda. Nunca desfaz a venda."""

        order = OrderRepository().get_order(order_id)
        if not order:
            raise FiscalValidationError("Venda não encontrada.")
        if order.cancelled:
            raise FiscalValidationError("Venda cancelada não pode emitir nota.")

        document = self.repository.get_by_order(order_id)
        if document and document.status == STATUS_AUTHORIZED:
            return document
        if document and document.status == STATUS_CANCELLED:
            raise FiscalValidationError("A nota desta venda foi cancelada.")

        if not document:
            document = self.repository.create_pending(
                order_id, self.config.provider, self.config.environment
            )

        if document.status == STATUS_AWAITING or document.retry_count > 0:
            return self.reenviar(document.id)
        return self._attempt(document, order)

    def reenviar(self, document_id: int):
        """Reenvia uma nota pendente consultando antes para não duplicar."""

        document = self.repository.get(document_id)
        if not document:
            raise FiscalValidationError("Nota fiscal não encontrada.")
        if document.status == STATUS_AUTHORIZED:
            return document
        if document.status == STATUS_CANCELLED:
            raise FiscalValidationError("Nota cancelada não pode ser reenviada.")

        order = OrderRepository().get_order(document.order_id)
        if not order:
            raise FiscalValidationError("Venda da nota não encontrada.")
        if order.cancelled:
            raise FiscalValidationError("A venda desta nota está cancelada.")

        should_query = (
            bool(document.access_key)
            or document.retry_count > 0
            or document.status == STATUS_AWAITING
        )
        if should_query:
            try:
                query = self._consult(document)
            except FiscalConfigError as error:
                return self._mark_pending(document, error, retry=False)
            except FiscalTransportError as error:
                return self._mark_pending(document, error, retry=True)

            updated = self._apply_query(document, query)
            if updated is not None:
                return updated

        return self._attempt(document, order)

    def reemitir_pendentes(self, limit: int = 50, force: bool = False) -> dict:
        """Reenvia em lote (usado pelo botão manual e pelo cron/systemd)."""

        config = self.config
        if not config.auto_retry and not force:
            return {
                "processed": 0,
                "authorized": 0,
                "pending": 0,
                "skipped": 0,
                "auto_retry": False,
                "documents": [],
            }

        now = datetime.now()
        statuses = set(PENDING_STATUSES)
        # Rejeitada/denegada não é documento válido: o reenvio manual também
        # tenta de novo. O automático (cron) continua só nas pendentes.
        if force:
            statuses |= {STATUS_REJECTED, STATUS_DENIED}
        documents = self.repository.list_by_status(statuses)
        processed = authorized = pending = skipped = attempts = 0
        details = []

        for document in documents:
            if attempts >= limit:
                break
            if not force and document.next_retry_at and document.next_retry_at > now:
                skipped += 1
                continue
            attempts += 1
            try:
                updated = self.reenviar(document.id)
            except FiscalError as error:
                pending += 1
                details.append(
                    {
                        "id": document.id,
                        "order_id": document.order_id,
                        "status": STATUS_PENDING,
                        "error": str(error),
                    }
                )
                continue

            processed += 1
            if updated.status == STATUS_AUTHORIZED:
                authorized += 1
            elif updated.status in PENDING_STATUSES:
                pending += 1
            details.append(
                {
                    "id": updated.id,
                    "order_id": updated.order_id,
                    "status": updated.status,
                    "error": updated.error_message or "",
                }
            )

        return {
            "processed": processed,
            "authorized": authorized,
            "pending": pending,
            "skipped": skipped,
            "auto_retry": config.auto_retry,
            "documents": details,
        }

    def _attempt(self, document, order):
        config = self.config

        try:
            if config.missing:
                raise FiscalConfigError(config.missing)
            request = self._build_request(order, config)
        except (FiscalConfigError, FiscalValidationError) as error:
            return self._mark_pending(document, error, retry=False)

        try:
            result = self.provider.emit(request)
        except FiscalConfigError as error:
            return self._mark_pending(document, error, retry=False)
        except FiscalTransportError as error:
            return self._mark_pending(document, error, retry=True)

        return self._apply_result(document, result)

    def _build_request(self, order, config: FiscalConfig):
        items = OrderRepository().get_order_items(order.id)
        products = {}
        for item in items:
            product = ProductRepository().get_product(item.product_id)
            if product is not None:
                products[item.product_id] = product

        methods = {
            method.id: method for method in PaymentMethodRepository().get_methods()
        }
        customer = (
            CustomerRepository().get_customer(order.customer_id)
            if order.customer_id
            else None
        )
        payment_rows = OrderRepository().get_order_payments(order.id)

        return build_request(
            order,
            items,
            products,
            methods,
            customer,
            config,
            payment_rows=payment_rows,
        )

    def _mark_pending(self, document, error: Exception, retry: bool):
        retry_count = document.retry_count + (1 if retry else 0)
        next_retry_at = datetime.now() + _retry_delay(retry_count) if retry else None
        return self.repository.update(
            document.id,
            status=STATUS_PENDING,
            error_code="",
            error_message=str(error),
            retry_count=retry_count,
            next_retry_at=next_retry_at,
        )

    def _apply_result(self, document, result):
        fields = {
            "status": result.status,
            "error_code": result.error_code or "",
            "error_message": result.error_message or "",
        }
        if result.access_key:
            fields["access_key"] = result.access_key
        if result.protocol:
            fields["protocol"] = result.protocol
        if result.series is not None:
            fields["series"] = result.series
        if result.number is not None:
            fields["number"] = result.number
        if result.xml:
            fields["xml"] = result.xml
        if result.danfe:
            fields["danfe"] = result.danfe
        if result.qr_code_url:
            fields["qr_code_url"] = result.qr_code_url

        if result.status == STATUS_AUTHORIZED:
            fields["authorized_at"] = datetime.now()
            fields["next_retry_at"] = None
            fields["error_code"] = ""
            fields["error_message"] = ""
        elif result.status == STATUS_AWAITING:
            fields["next_retry_at"] = datetime.now() + timedelta(minutes=5)
        elif result.status in (STATUS_REJECTED, STATUS_DENIED):
            fields["retry_count"] = document.retry_count + 1
            fields["next_retry_at"] = datetime.now() + _retry_delay(
                document.retry_count + 1
            )

        return self.repository.update(document.id, **fields)

    # --------------------------------------------------------------- Consultar
    def _consult(self, document) -> FiscalQueryResult:
        if document.access_key:
            return self.provider.query(access_key=document.access_key)
        return self.provider.query(identifier=f"VENDA-{document.order_id}")

    def _apply_query(self, document, query: FiscalQueryResult):
        if not query.found:
            return None

        status = query.status
        if status == STATUS_AUTHORIZED:
            fields = {
                "status": STATUS_AUTHORIZED,
                "authorized_at": document.authorized_at or datetime.now(),
                "next_retry_at": None,
                "error_code": "",
                "error_message": "",
            }
            if query.access_key:
                fields["access_key"] = query.access_key
            if query.protocol:
                fields["protocol"] = query.protocol
            if query.series is not None:
                fields["series"] = query.series
            if query.number is not None:
                fields["number"] = query.number
            if query.xml:
                fields["xml"] = query.xml
            if query.danfe:
                fields["danfe"] = query.danfe
            if query.qr_code_url:
                fields["qr_code_url"] = query.qr_code_url
            return self.repository.update(document.id, **fields)

        if status == STATUS_CANCELLED:
            return self.repository.update(
                document.id,
                status=STATUS_CANCELLED,
                cancelled_at=document.cancelled_at or datetime.now(),
                error_code=query.error_code or "",
                error_message=query.error_message or "",
            )

        if status == STATUS_AWAITING:
            return self.repository.update(
                document.id,
                status=STATUS_AWAITING,
                next_retry_at=datetime.now() + timedelta(minutes=5),
                error_code=query.error_code or "",
                error_message=query.error_message or "",
            )

        # Rejeitada/denegada: não é documento válido, pode tentar de novo.
        return None

    # ------------------------------------------------------------- Cancelamento
    def cancelar(self, document_id: int, justificativa: str):
        justificativa = (justificativa or "").strip()
        if len(justificativa) < 15:
            raise FiscalValidationError(
                "A justificativa do cancelamento precisa ter ao menos 15 caracteres."
            )
        if len(justificativa) > 1000:
            raise FiscalValidationError(
                "A justificativa do cancelamento pode ter no máximo 1000 caracteres."
            )

        document = self.repository.get(document_id)
        if not document:
            raise FiscalValidationError("Nota fiscal não encontrada.")
        if document.status == STATUS_CANCELLED:
            return document

        if document.status in (STATUS_PENDING, STATUS_REJECTED, STATUS_DENIED):
            return self.repository.update(
                document.id,
                status=STATUS_CANCELLED,
                cancelled_at=datetime.now(),
                cancel_reason=justificativa,
            )

        if not document.access_key:
            raise FiscalCancellationError(
                "A nota ainda não tem chave de acesso; aguarde o processamento "
                "antes de cancelar."
            )

        try:
            result = self.provider.cancel(document.access_key, justificativa)
        except FiscalTransportError as error:
            raise FiscalCancellationError(str(error)) from error

        if not result.ok:
            raise FiscalCancellationError(
                result.error_message or "A SEFAZ recusou o cancelamento da nota."
            )

        return self.repository.update(
            document.id,
            status=STATUS_CANCELLED,
            cancelled_at=datetime.now(),
            cancel_reason=justificativa,
            protocol=result.protocol or document.protocol,
        )

    def cancelar_por_venda(self, order_id: int, justificativa: str = ""):
        """Cancela a nota junto com a venda; devolve None se não houver nota."""

        document = self.repository.get_by_order(order_id)
        if not document or document.status == STATUS_CANCELLED:
            return document

        if document.status in (STATUS_PENDING, STATUS_REJECTED, STATUS_DENIED):
            reason = (justificativa or "Venda cancelada").strip()
            return self.repository.update(
                document.id,
                status=STATUS_CANCELLED,
                cancelled_at=datetime.now(),
                cancel_reason=reason,
            )

        return self.cancelar(document.id, justificativa)

    # ----------------------------------------------------------------- Arquivos
    def obter_xml(self, document_id: int) -> bytes:
        document = self.repository.get(document_id)
        if not document:
            raise FiscalValidationError("Nota fiscal não encontrada.")

        if document.xml:
            return document.xml.encode("utf-8")
        if not document.access_key:
            raise FiscalValidationError("A nota ainda não possui XML autorizado.")

        data = self.provider.download_xml(document.access_key)
        try:
            self.repository.update(
                document.id, xml=data.decode("utf-8", errors="replace")
            )
        except Exception:  # cache é best-effort
            pass
        return data

    def obter_danfe(self, document_id: int) -> bytes:
        document = self.repository.get(document_id)
        if not document:
            raise FiscalValidationError("Nota fiscal não encontrada.")

        if document.danfe:
            try:
                return base64.b64decode(document.danfe)
            except (ValueError, TypeError):
                pass
        if not document.access_key:
            raise FiscalValidationError("A nota ainda não possui DANFE disponível.")

        data = self.provider.download_danfe(document.access_key)
        try:
            self.repository.update(
                document.id, danfe=base64.b64encode(data).decode("ascii")
            )
        except Exception:  # cache é best-effort
            pass
        return data

    # ------------------------------------------------------------------ Status
    def documento_por_venda(self, order_id: int):
        return self.repository.get_by_order(order_id)

    def listar_pendentes(self) -> List:
        return self.repository.list_by_status(PENDING_STATUSES)

    def listar_todos(self) -> List:
        return self.repository.list_all()

    def testar_conexao(self):
        return self.provider.test_connection()
