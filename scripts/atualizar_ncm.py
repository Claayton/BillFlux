"""Atualiza a tabela local de NCMs vigentes usada na validação fiscal.

Fonte oficial: Portal Único do Siscomex (nomenclatura em JSON).
A tabela embutida permite validar o NCM sem internet no balcão.

Uso:
    venv/bin/python scripts/atualizar_ncm.py
    venv/bin/python scripts/atualizar_ncm.py --arquivo /caminho/ncm.json
"""

import argparse
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

URL_PADRAO = (
    "https://portalunico.siscomex.gov.br/classif/api/publico/"
    "nomenclatura/download/json?perfil=PUBLICO"
)
SAIDA_PADRAO = (
    Path(__file__).resolve().parent.parent
    / "billflux"
    / "services"
    / "fiscal"
    / "data"
    / "ncm_vigente.txt"
)


def _data(valor):
    try:
        return dt.datetime.strptime(str(valor), "%d/%m/%Y").date()
    except (TypeError, ValueError):
        return None


def extrair_codigos(payload, hoje=None):
    """Códigos NCM de 8 dígitos vigentes na data informada.

    A nomenclatura traz vários níveis (2, 4, 5, 6, 8 e 9 dígitos). Só o nível
    de 8 dígitos (exibido como ``0101.21.00``) é um NCM aceito pela SEFAZ.
    """

    hoje = hoje or dt.date.today()
    codigos = set()
    for item in payload.get("Nomenclaturas") or []:
        codigo = str(item.get("Codigo") or "")
        if len(codigo) != 10 or codigo.count(".") != 2:
            continue
        digitos = codigo.replace(".", "")
        if len(digitos) != 8 or not digitos.isdigit():
            continue
        fim = _data(item.get("Data_Fim"))
        if fim is not None and fim < hoje:
            continue
        codigos.add(digitos)
    return sorted(codigos)


def baixar(url, timeout=90):
    request = urllib.request.Request(url, headers={"User-Agent": "BeeFlux/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def renderizar(codigos, atualizado_em=None, fonte=URL_PADRAO):
    atualizado_em = atualizado_em or dt.date.today()
    linhas = [
        "# Tabela de NCMs vigentes (fonte: Portal Único do Siscomex).",
        f"# Fonte: {fonte}",
        f"# Atualizado em: {atualizado_em.isoformat()}",
        f"# Total: {len(codigos)}",
        "",
    ]
    linhas.extend(codigos)
    return "\n".join(linhas) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=URL_PADRAO)
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    parser.add_argument(
        "--arquivo",
        type=Path,
        help="usa um JSON já baixado em vez de consultar o Siscomex",
    )
    args = parser.parse_args(argv)

    payload = (
        json.loads(args.arquivo.read_text("utf-8"))
        if args.arquivo
        else baixar(args.url)
    )
    codigos = extrair_codigos(payload)
    if not codigos:
        print("Nenhum NCM vigente encontrado; arquivo não alterado.", file=sys.stderr)
        return 1

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(renderizar(codigos), encoding="utf-8")
    print(f"{len(codigos)} NCMs vigentes gravados em {args.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
