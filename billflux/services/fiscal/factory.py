"""Fábrica de provedores fiscais."""

from billflux.services.fiscal.base import FiscalConfigError, FiscalProvider
from billflux.services.fiscal.brasilnfe import BrasilNFeProvider
from billflux.services.fiscal.config import FiscalConfig


def get_provider(config: FiscalConfig) -> FiscalProvider:
    """Devolve o adapter configurado (hoje só Brasil NFe)."""

    if config.provider != "brasilnfe":
        raise FiscalConfigError([f"provedor fiscal suportado ({config.provider})"])
    if not config.token:
        raise FiscalConfigError(["token do provedor (BRASILNFE_TOKEN)"])
    return BrasilNFeProvider(token=config.token)
