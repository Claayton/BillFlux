"""Configuração da emissão fiscal, lida das settings + ambiente."""

import os
from dataclasses import dataclass
from typing import List, Optional

from billflux.infra.repository.settings_repository import SettingsRepository

TOKEN_ENV = "BRASILNFE_TOKEN"
PROVIDER_ENV = "FISCAL_PROVIDER"

PROVIDER_DEFAULT = "brasilnfe"
ENVIRONMENTS = {"homologacao", "producao"}
PRINT_MODES = {"thermal", "pdf", "none"}
CRT_VALUES = {"1", "2", "3"}


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _as_int(value) -> Optional[int]:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


@dataclass(frozen=True)
class FiscalConfig:
    """Retrato da configuração usada numa emissão."""

    provider: str
    environment: str
    token: str
    cnpj: str
    ie: str
    crt: str
    print_mode: str
    auto_retry: bool
    series: Optional[int] = None
    last_number: Optional[int] = None

    @property
    def is_homologation(self) -> bool:
        return self.environment == "homologacao"

    @property
    def tipo_ambiente(self) -> int:
        """Código do ambiente na SEFAZ: 1 produção, 2 homologação."""

        return 2 if self.is_homologation else 1

    @property
    def missing(self) -> List[str]:
        """O que falta para conseguir emitir (mensagens para o usuário)."""

        missing = []
        if self.provider != PROVIDER_DEFAULT:
            missing.append(f"provedor fiscal suportado ({self.provider})")
        if not self.token:
            missing.append("token do provedor (BRASILNFE_TOKEN)")
        if not self.cnpj:
            missing.append("CNPJ da empresa")
        if not self.ie:
            missing.append("inscrição estadual (IE)")
        return missing

    @property
    def ready(self) -> bool:
        return not self.missing


def load_config() -> FiscalConfig:
    """Monta a configuração a partir das settings e do ambiente."""

    settings = SettingsRepository().get_all()

    provider = (
        os.environ.get(PROVIDER_ENV)
        or settings.get("fiscal.provider")
        or PROVIDER_DEFAULT
    ).strip()

    environment = (settings.get("fiscal.environment") or "homologacao").strip()
    if environment not in ENVIRONMENTS:
        environment = "homologacao"

    print_mode = (settings.get("fiscal.print_mode") or "thermal").strip()
    if print_mode not in PRINT_MODES:
        print_mode = "thermal"

    crt = (settings.get("fiscal.crt") or "1").strip()
    if crt not in CRT_VALUES:
        crt = "1"

    return FiscalConfig(
        provider=provider,
        environment=environment,
        token=(os.environ.get(TOKEN_ENV) or "").strip(),
        cnpj=(settings.get("company.cnpj") or "").strip(),
        ie=(settings.get("fiscal.ie") or "").strip(),
        crt=crt,
        print_mode=print_mode,
        auto_retry=_as_bool(settings.get("fiscal.auto_retry", "true")),
        series=_as_int(settings.get("fiscal.nfce_series")),
        last_number=_as_int(settings.get("fiscal.nfce_last_number")),
    )
