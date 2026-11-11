"""Endpoints de configuração e emissão fiscal (NFC-e)."""

import os
from io import BytesIO

from flask import request, send_file
from sqlmodel import select

from billflux.api import bp, api_error, api_login_required, api_response
from billflux.infra.config.database import get_session
from billflux.infra.entities.product import Product as ProductModel
from billflux.infra.repository.customer_repository import CustomerRepository
from billflux.infra.repository.fiscal_document_repository import (
    FiscalDocumentRepository,
)
from billflux.infra.repository.order_repository import OrderRepository
from billflux.infra.repository.settings_repository import SettingsRepository
from billflux.services.fiscal import (
    PENDING_STATUSES,
    STATUS_AUTHORIZED,
    STATUS_DENIED,
    STATUS_REJECTED,
    FiscalCancellationError,
    FiscalConfigError,
    FiscalError,
    FiscalService,
    FiscalTransportError,
    FiscalValidationError,
)
from billflux.services.fiscal.ncm import is_valid_ncm

PROVIDER_DEFAULT = "brasilnfe"
TOKEN_ENV = "BRASILNFE_TOKEN"
ENVIRONMENTS = {"homologacao", "producao"}
PRINT_MODES = {"thermal", "pdf", "none"}
CRT_VALUES = {"1", "2", "3"}


def _fiscal_settings():
    settings = SettingsRepository().get_all()
    provider = settings.get("fiscal.provider") or PROVIDER_DEFAULT
    environment = settings.get("fiscal.environment") or "homologacao"
    if environment not in ENVIRONMENTS:
        environment = "homologacao"
    print_mode = settings.get("fiscal.print_mode") or "thermal"
    if print_mode not in PRINT_MODES:
        print_mode = "thermal"
    crt = settings.get("fiscal.crt") or "1"
    if crt not in CRT_VALUES:
        crt = "1"
    return {
        "provider": provider,
        "environment": environment,
        "print_mode": print_mode,
        "auto_retry": str(settings.get("fiscal.auto_retry") or "true").strip().lower()
        in ("1", "true", "yes", "on"),
        "crt": crt,
        "ie": (settings.get("fiscal.ie") or "").strip(),
        "cnpj": (settings.get("company.cnpj") or "").strip(),
        "nfce_series": (settings.get("fiscal.nfce_series") or "").strip(),
        "nfce_last_number": (settings.get("fiscal.nfce_last_number") or "").strip(),
    }


def _missing_fiscal(product):
    """Campos que impedem a emissão (só o NCM bloqueia; o resto tem padrão)."""
    ncm = (product.ncm or "").strip()
    if not ncm:
        return ["ncm"]
    if not is_valid_ncm(ncm):
        return ["ncm_invalido"]
    return []


def _pending_products():
    session = get_session()
    try:
        with session:
            products = session.exec(
                select(ProductModel).where(ProductModel.active.is_(True))
            ).all()
            pending = []
            for product in products:
                missing = _missing_fiscal(product)
                if missing:
                    pending.append(
                        {
                            "id": product.id,
                            "name": product.name,
                            "missing": missing,
                        }
                    )
            return pending
    finally:
        session.close()


@bp.route("/fiscal/status")
@api_login_required
def fiscal_status():
    """Configuração fiscal atual + pendências + se está pronto para emitir."""
    settings = _fiscal_settings()
    token_configured = bool(os.environ.get(TOKEN_ENV, "").strip())
    # CFOP/CSOSN/origem têm padrão; somente o NCM bloqueia a emissão.
    pending = _pending_products()
    pending_documents = FiscalDocumentRepository().list_by_status(PENDING_STATUSES)

    missing = []
    if not token_configured:
        missing.append("token")
    if not settings["cnpj"]:
        missing.append("cnpj")
    if not settings["ie"]:
        missing.append("ie")
    if pending:
        missing.append("produtos_sem_dados_fiscais")

    return api_response(
        {
            "provider": settings["provider"],
            "environment": settings["environment"],
            "token_configured": token_configured,
            "token_env": TOKEN_ENV,
            "emitente": {
                "cnpj": settings["cnpj"],
                "ie": settings["ie"],
                "crt": settings["crt"],
            },
            "print_mode": settings["print_mode"],
            "auto_retry": settings["auto_retry"],
            "nfce_series": settings["nfce_series"],
            "nfce_last_number": settings["nfce_last_number"],
            "pending_products": len(pending),
            "pending_documents": len(pending_documents),
            "missing": missing,
            "ready": not missing,
        }
    )


@bp.route("/fiscal/pending-products")
@api_login_required
def fiscal_pending_products():
    """Produtos ativos sem NCM ou com NCM fora da tabela vigente."""
    pending = _pending_products()
    return api_response({"count": len(pending), "products": pending})


# --------------------------------------------------------------------------
# Fase 2: emissão, reenvio e cancelamento
# --------------------------------------------------------------------------


def _serialize_document(document):
    return {
        "id": document.id,
        "order_id": document.order_id,
        "provider": document.provider,
        "model": document.model,
        "environment": document.environment,
        "status": document.status,
        "series": document.series,
        "number": document.number,
        "access_key": document.access_key,
        "protocol": document.protocol,
        "qr_code_url": document.qr_code_url,
        "error_code": document.error_code,
        "error_message": document.error_message,
        "retry_count": document.retry_count,
        "next_retry_at": document.next_retry_at,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "authorized_at": document.authorized_at,
        "cancelled_at": document.cancelled_at,
        "cancel_reason": document.cancel_reason,
        "has_xml": bool(document.xml),
        "has_danfe": bool(document.danfe),
    }


def _document_response(document):
    return api_response(
        {
            "ok": document.status == STATUS_AUTHORIZED,
            "status": document.status,
            "message": document.error_message or "",
            "document": _serialize_document(document),
        }
    )


@bp.route("/fiscal/emitir", methods=["POST"])
@api_login_required
def fiscal_emitir():
    """Emite (ou tenta novamente) a NFC-e de uma venda do PDV."""

    data = request.get_json(silent=True) or {}
    try:
        order_id = int(data.get("order_id"))
    except (TypeError, ValueError):
        return api_error("Informe a venda para emitir a nota.", 400)

    try:
        document = FiscalService().emitir(order_id)
    except FiscalError as error:
        return api_error(str(error), 400)
    return _document_response(document)


@bp.route("/fiscal/<int:document_id>/reenviar", methods=["POST"])
@api_login_required
def fiscal_reenviar(document_id):
    """Reenvia uma nota pendente (consultando antes para não duplicar)."""

    try:
        document = FiscalService().reenviar(document_id)
    except FiscalError as error:
        return api_error(str(error), 400)
    return _document_response(document)


@bp.route("/fiscal/reenviar-pendentes", methods=["POST"])
@api_login_required
def fiscal_reenviar_pendentes():
    """Reenvia em lote as notas pendentes (botão manual)."""

    data = request.get_json(silent=True) or {}
    try:
        limit = int(data.get("limit") or 50)
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(limit, 200))

    summary = FiscalService().reemitir_pendentes(limit=limit, force=True)
    return api_response(summary)


@bp.route("/fiscal/<int:document_id>/cancelar", methods=["POST"])
@api_login_required
def fiscal_cancelar(document_id):
    """Cancela uma nota autorizada com justificativa (15 a 1000 caracteres)."""

    data = request.get_json(silent=True) or {}
    try:
        document = FiscalService().cancelar(
            document_id, data.get("justificativa") or ""
        )
    except (FiscalValidationError, FiscalCancellationError) as error:
        return api_error(str(error), 400)
    except FiscalError as error:
        return api_error(str(error), 400)

    return api_response({"ok": True, "document": _serialize_document(document)})


@bp.route("/fiscal/pendentes")
@api_login_required
def fiscal_pendentes():
    """Notas pendentes (banner da tela inicial e tela de pendências fiscais)."""

    # Pendentes + rejeitadas/denegadas: tudo que ainda não tem NFC-e válida
    # aparece no banner para o operador reenviar.
    documents = FiscalDocumentRepository().list_by_status(
        set(PENDING_STATUSES) | {STATUS_REJECTED, STATUS_DENIED}
    )
    orders = {order.id: order for order in OrderRepository().get_orders()}
    customers = {c.id: c.name for c in CustomerRepository().get_customers()}

    items = []
    for document in documents:
        data = _serialize_document(document)
        order = orders.get(document.order_id)
        data["order"] = {
            "id": document.order_id,
            "total": float(order.total) if order else None,
            "created_at": order.created_at if order else None,
            "customer_name": (customers.get(order.customer_id, "") if order else ""),
        }
        items.append(data)

    return api_response({"count": len(items), "documents": items})


@bp.route("/fiscal/vendas/<int:order_id>")
@api_login_required
def fiscal_por_venda(order_id):
    """Situação fiscal de uma venda específica."""

    document = FiscalDocumentRepository().get_by_order(order_id)
    return api_response(
        {"document": _serialize_document(document) if document else None}
    )


@bp.route("/fiscal/<int:document_id>/xml")
@api_login_required
def fiscal_xml(document_id):
    """Baixa o XML autorizado da nota."""

    try:
        content = FiscalService().obter_xml(document_id)
    except FiscalError as error:
        return api_error(str(error), 400)

    return send_file(
        BytesIO(content),
        mimetype="application/xml",
        as_attachment=True,
        download_name=f"nfce-{document_id}.xml",
    )


@bp.route("/fiscal/<int:document_id>/danfe")
@api_login_required
def fiscal_danfe(document_id):
    """Baixa o DANFE da nota (PDF ou HTML, conforme o provedor)."""

    try:
        content = FiscalService().obter_danfe(document_id)
    except FiscalError as error:
        return api_error(str(error), 400)

    head = content.lstrip()[:8].lower()
    if head.startswith(b"%pdf"):
        mimetype, extension, attachment = "application/pdf", "pdf", True
    elif head.startswith(b"<"):
        # HTML do provedor pode conter dados do produto: nunca renderizar
        # inline na origem do app (evita XSS); o download vira anexo.
        mimetype, extension, attachment = "text/html", "html", True
    else:
        mimetype, extension, attachment = "application/octet-stream", "bin", True

    return send_file(
        BytesIO(content),
        mimetype=mimetype,
        as_attachment=attachment,
        download_name=f"danfe-{document_id}.{extension}",
    )


@bp.route("/fiscal/testar-conexao", methods=["POST"])
@api_login_required
def fiscal_testar_conexao():
    """Consulta o status da SEFAZ pelo provedor configurado."""

    try:
        result = FiscalService().testar_conexao()
    except FiscalConfigError as error:
        return api_error(str(error), 400)
    except FiscalTransportError as error:
        return api_error(str(error), 502)
    except FiscalError as error:
        return api_error(str(error), 400)

    return api_response(
        {
            "ok": result.ok,
            "code": result.code,
            "message": result.message,
            "warnings": result.warnings,
        }
    )
