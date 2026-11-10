"""Endpoints de configuração fiscal (NFC-e).

Fase 1: somente leitura de configuração/pendências — nenhuma emissão.
"""

import os

from sqlmodel import select

from billflux.api import bp, api_login_required, api_response
from billflux.infra.config.database import get_session
from billflux.infra.entities.product import Product as ProductModel
from billflux.infra.repository.settings_repository import SettingsRepository

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
        "auto_retry": (settings.get("fiscal.auto_retry") or "true") == "true",
        "crt": crt,
        "ie": (settings.get("fiscal.ie") or "").strip(),
        "cnpj": (settings.get("company.cnpj") or "").strip(),
        "nfce_series": (settings.get("fiscal.nfce_series") or "").strip(),
        "nfce_last_number": (settings.get("fiscal.nfce_last_number") or "").strip(),
    }


def _missing_fiscal(product, crt):
    """Campos fiscais que faltam no produto (vazio = pronto para emitir)."""
    missing = []
    if not (product.ncm or "").strip():
        missing.append("ncm")
    if not (product.cfop or "").strip():
        missing.append("cfop")
    # Simples usa CSOSN; Regime Normal usa CST.
    if crt == "3":
        if not (product.cst or "").strip():
            missing.append("cst")
    elif not (product.csosn or "").strip():
        missing.append("csosn")
    return missing


def _pending_products(crt):
    session = get_session()
    try:
        with session:
            products = session.exec(
                select(ProductModel).where(ProductModel.active.is_(True))
            ).all()
            pending = []
            for product in products:
                missing = _missing_fiscal(product, crt)
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
    pending = _pending_products(settings["crt"])

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
            "missing": missing,
            "ready": not missing,
        }
    )


@bp.route("/fiscal/pending-products")
@api_login_required
def fiscal_pending_products():
    """Produtos ativos sem os dados fiscais mínimos para emitir NFC-e."""
    settings = _fiscal_settings()
    pending = _pending_products(settings["crt"])
    return api_response({"count": len(pending), "products": pending})
