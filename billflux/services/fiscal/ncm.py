"""Tabela local de NCMs vigentes (Siscomex) para validar o cadastro fiscal.

A lista fica embutida no projeto para a validação funcionar offline: o PDV
não pode depender da internet para salvar um produto. Atualize quando a
Siscomex publicar uma tabela nova:

    venv/bin/python scripts/atualizar_ncm.py
"""

from functools import lru_cache
from pathlib import Path
from typing import FrozenSet

TABELA = Path(__file__).with_name("data") / "ncm_vigente.txt"


def normalize_ncm(value) -> str:
    """Devolve só os dígitos do NCM (aceita ``2202.10.00``)."""

    return "".join(char for char in str(value or "") if char.isdigit())


@lru_cache(maxsize=1)
def _codigos() -> FrozenSet[str]:
    try:
        linhas = TABELA.read_text(encoding="utf-8").splitlines()
    except OSError:
        return frozenset()
    return frozenset(
        linha.strip() for linha in linhas if linha.strip() and not linha.startswith("#")
    )


def is_valid_ncm(value) -> bool:
    """True quando o código existe na tabela vigente embutida.

    Se a tabela não puder ser lida (deploy sem o arquivo), a validação
    degrada para o formato de 8 dígitos em vez de bloquear tudo.
    """

    codigo = normalize_ncm(value)
    if len(codigo) != 8:
        return False

    codigos = _codigos()
    if not codigos:
        return True
    return codigo in codigos


def table_info() -> dict:
    """Data de atualização, fonte e total de NCMs (cabeçalho do arquivo)."""

    info = {"updated_at": None, "source": None, "count": len(_codigos())}
    try:
        with TABELA.open(encoding="utf-8") as arquivo:
            for linha in arquivo:
                if linha.startswith("# Atualizado em:"):
                    info["updated_at"] = linha.split(":", 1)[1].strip()
                elif linha.startswith("# Fonte:"):
                    info["source"] = linha.split(":", 1)[1].strip()
                elif not linha.startswith("#") and linha.strip():
                    break
    except OSError:
        pass
    return info
