"""Module for repository to Setting (configurações editáveis)"""

from typing import Dict, List

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.setting import Setting as SettingModel

#: Chaves que a API permite ler/escrever. Todo o resto é ignorado,
#: e segredos (ex.: secret_key) nunca passam por aqui.
ALLOWED_KEYS = frozenset(
    {
        "company.name",
        "company.cnpj",
        "company.address",
        "company.phone",
        "receipt.width",
        "receipt.header",
        "receipt.footer",
        "pdv.auto_print",
        "stock.default_min",
    }
)


class SettingsRepository:
    """Setting table data manipulation"""

    def get_all(self) -> Dict[str, str]:
        """Todas as chaves permitidas (ausentes voltam como '')."""
        session = get_session()
        try:
            with session:
                rows = session.exec(select(SettingModel)).all()
                stored = {r.key: (r.value or "") for r in rows}
        finally:
            session.close()
        return {key: stored.get(key, "") for key in sorted(ALLOWED_KEYS)}

    def set_many(self, values: Dict[str, str]) -> Dict[str, str]:
        """Grava somente chaves permitidas; ignora o resto."""
        session = get_session()
        try:
            with session:
                for key, value in (values or {}).items():
                    if key not in ALLOWED_KEYS:
                        continue
                    model = session.get(SettingModel, key)
                    if model is None:
                        model = SettingModel(key=key, value=value)
                    else:
                        model.value = value
                    session.add(model)
                session.commit()
        finally:
            session.close()
        return self.get_all()

    def get_keys(self) -> List[str]:
        """Apenas para testes/inspeção."""
        return sorted(ALLOWED_KEYS)
