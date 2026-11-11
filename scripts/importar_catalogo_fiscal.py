"""Importa os campos fiscais da planilha revisada para o catálogo.

A planilha é a exportada pelo BeeFlux e preenchida pelo contador. O casamento
é sempre pelo **ID** do produto: nome parecido não é usado.

Por padrão o script só mostra o que mudaria (dry-run). Para gravar de verdade,
use ``--aplicar``.

O banco é acessado pela mesma camada do app (SQLAlchemy), então o script roda
tanto no dev (SQLite) quanto em produção (Postgres). A URL vem de
``--db-url`` ou, na falta dela, de ``BILLFLUX_DATABASE__URL``.

Uso no dev (SQLite):

    venv/bin/python scripts/importar_catalogo_fiscal.py \
        --arquivo ~/Downloads/catalogo-fiscal-preenchido-2026-11-11.xlsx

Uso em produção (Docker, Postgres), dentro do container da API:

    docker compose -f docker-compose-prod.yml exec -T api \
        python scripts/importar_catalogo_fiscal.py \
        --arquivo /tmp/catalogo-fiscal-preenchido-2026-11-11.xlsx

Antes do ``--aplicar`` em Postgres, faça o ``pg_dump`` e confirme com
``--backup-feito``. No SQLite o backup é automático.
"""

import argparse
import csv
import datetime as dt
import re
import shutil
import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple

from openpyxl import load_workbook
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from billflux.config import settings  # noqa: E402
from billflux.services.fiscal.ncm import is_valid_ncm  # noqa: E402

CAMPOS = ("ncm", "cest", "cfop", "csosn", "cst", "origem", "fiscal_unit")
TAMANHOS = {"ncm": 8, "cest": 7, "cfop": 4, "csosn": 3, "cst": 2}
TITULOS = {
    "ID": "id",
    "Nome": "nome",
    "NCM": "ncm",
    "CEST": "cest",
    "CFOP": "cfop",
    "CSOSN": "csosn",
    "CST": "cst",
    "Origem": "origem",
    "Unidade fiscal": "fiscal_unit",
}
COLUNAS_BANCO = (
    "id",
    "name",
    "ncm",
    "cest",
    "cfop",
    "csosn",
    "cst",
    "origem",
    "fiscal_unit",
)


def url_sem_senha(url: str) -> str:
    """Mostra a URL do banco sem expor a senha no terminal/log."""

    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        # URL inválida não deve vazar credencial nenhuma.
        return "(URL do banco não exibida)"


def somente_digitos(valor) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def normalizar(valor) -> str:
    return "" if valor is None else str(valor).strip()


def normalizar_nome(valor) -> str:
    """Compara nomes sem acento, caixa ou pontuação."""

    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", texto.lower()).strip()


def ler_planilha(caminho: Path) -> Tuple[List[dict], List[str]]:
    """Devolve as linhas fiscais e a lista de erros de formato."""

    workbook = load_workbook(caminho, read_only=True, data_only=True)
    planilha = workbook["Catálogo fiscal"]
    linhas = planilha.iter_rows(values_only=True)
    cabecalho = next(linhas, None)
    if not cabecalho:
        raise SystemExit("Planilha vazia: esperava o cabeçalho na primeira linha.")

    indices = {}
    for posicao, titulo in enumerate(cabecalho):
        chave = TITULOS.get(str(titulo or "").strip())
        if chave:
            indices[chave] = posicao
    if "id" not in indices or "ncm" not in indices:
        raise SystemExit("Planilha sem as colunas obrigatórias ID e NCM.")

    registros, erros = [], []
    for numero, linha in enumerate(linhas, start=2):
        bruto_id = linha[indices["id"]] if indices["id"] < len(linha) else None
        try:
            produto_id = int(bruto_id)
        except (TypeError, ValueError):
            if any(valor not in (None, "") for valor in linha):
                erros.append(f"linha {numero}: ID inválido ({bruto_id!r})")
            continue

        valores: Dict[str, object] = {}
        problema = None
        pos_nome = indices.get("nome")
        nome_planilha = ""
        if pos_nome is not None and pos_nome < len(linha):
            nome_planilha = str(linha[pos_nome] or "").strip()

        for campo in CAMPOS:
            posicao = indices.get(campo)
            if posicao is None or posicao >= len(linha):
                continue
            bruto = linha[posicao]

            if campo == "origem":
                if bruto in (None, ""):
                    continue
                try:
                    origem = int(bruto)
                except (TypeError, ValueError):
                    problema = f"origem inválida ({bruto!r})"
                    break
                if origem < 0 or origem > 8:
                    problema = f"origem fora de 0-8 ({origem})"
                    break
                valores[campo] = origem
                continue

            if campo == "fiscal_unit":
                texto = str(bruto or "").strip().upper()
                if texto:
                    valores[campo] = texto[:6]
                continue

            digitos = somente_digitos(bruto)
            if not digitos:
                continue
            esperado = TAMANHOS[campo]
            if len(digitos) != esperado:
                problema = f"{campo} com {len(digitos)} dígitos (esperado {esperado})"
                break
            if campo == "ncm" and not is_valid_ncm(digitos):
                problema = f"NCM {digitos} não existe na tabela vigente"
                break
            valores[campo] = digitos

        if problema:
            erros.append(f"linha {numero} (ID {produto_id}): {problema}")
            continue
        if not valores.get("ncm"):
            # Sem NCM não há o que importar; o produto continua pendente.
            continue
        registros.append({"id": produto_id, "nome": nome_planilha, **valores})

    workbook.close()
    return registros, erros


def comparar(
    conexao, registros: List[dict]
) -> Tuple[List[dict], List[dict], List[Tuple[int, str, str]]]:
    """Devolve (mudancas, nao_encontrados, nomes_divergentes)."""

    sql = text(f"select {', '.join(COLUNAS_BANCO)} from product")
    existentes = {linha["id"]: dict(linha) for linha in conexao.execute(sql).mappings()}
    mudancas, faltantes, divergentes = [], [], []
    for registro in registros:
        atual = existentes.get(registro["id"])
        if atual is None:
            faltantes.append(registro)
            continue

        nome_planilha = normalizar_nome(registro.get("nome"))
        nome_banco = normalizar_nome(atual.get("name"))
        if nome_planilha and nome_planilha != nome_banco:
            divergentes.append(
                (
                    registro["id"],
                    registro.get("nome") or "",
                    atual.get("name") or "",
                )
            )

        alteracoes = {}
        for campo in CAMPOS:
            if campo not in registro:
                continue
            antes, depois = normalizar(atual.get(campo)), normalizar(registro[campo])
            if campo == "origem":
                antes = str(int(atual.get(campo) or 0))
                depois = str(int(registro[campo]))
            elif campo in TAMANHOS:
                antes = somente_digitos(antes)
                depois = somente_digitos(depois)
            if antes != depois:
                alteracoes[campo] = (antes, depois)

        if alteracoes:
            mudancas.append(
                {
                    "id": registro["id"],
                    "nome": atual.get("name") or "",
                    "campos": alteracoes,
                }
            )
    return mudancas, faltantes, divergentes


def salvar_relatorio(caminho: Path, mudancas: List[dict]) -> None:
    with caminho.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["ID", "Nome", "Campo", "Antes", "Depois"])
        for mudanca in mudancas:
            for campo, (antes, depois) in mudanca["campos"].items():
                escritor.writerow(
                    [mudanca["id"], mudanca["nome"], campo, antes, depois]
                )


def fazer_backup(engine, backup_feito: bool):
    """Backup do SQLite (automático) ou confirmação do dump do Postgres."""

    if engine.dialect.name == "sqlite":
        arquivo = Path(engine.url.database or "")
        if not arquivo.exists():
            raise SystemExit(f"Banco SQLite não encontrado: {arquivo}")
        carimbo = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        destino = arquivo.with_name(f"{arquivo.name}.bak-{carimbo}")
        shutil.copy2(arquivo, destino)
        return destino

    if not backup_feito:
        raise SystemExit(
            "Banco não é SQLite. Faça o pg_dump antes de aplicar e rode de "
            "novo com --backup-feito:\n\n"
            "  docker compose -f docker-compose-prod.yml exec -T postgres \\\n"
            '    pg_dump -U "${POSTGRES_USER:-billflux}" '
            '"${POSTGRES_DB:-billflux}" | gzip > backup-antes-fiscal.sql.gz'
        )
    return None


def aplicar(conexao, mudancas: List[dict]) -> None:
    for mudanca in mudancas:
        campos = list(mudanca["campos"].keys())
        sets = ", ".join(f"{campo} = :{campo}" for campo in campos)
        parametros = {campo: mudanca["campos"][campo][1] for campo in campos}
        parametros["id"] = mudanca["id"]
        conexao.execute(text(f"update product set {sets} where id = :id"), parametros)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arquivo", required=True, type=Path)
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument(
        "--db", type=Path, help="Caminho do arquivo SQLite (atalho para dev)."
    )
    grupo.add_argument(
        "--db-url",
        help="URL SQLAlchemy (ex.: postgresql://usuario:senha@host/banco).",
    )
    parser.add_argument("--aplicar", action="store_true")
    parser.add_argument(
        "--backup-feito",
        action="store_true",
        help="Confirma que o backup do Postgres já foi feito.",
    )
    parser.add_argument(
        "--permitir-nomes-divergentes",
        action="store_true",
        help="Segue mesmo se os nomes do banco não baterem com a planilha.",
    )
    parser.add_argument(
        "--relatorio",
        type=Path,
        help="Salva o diff completo em CSV (padrão: ao lado da planilha).",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=40,
        help="Quantas mudanças mostrar no terminal (padrão: 40).",
    )
    args = parser.parse_args()

    if not args.arquivo.exists():
        raise SystemExit(f"Planilha não encontrada: {args.arquivo}")

    if args.db:
        if not args.db.exists():
            raise SystemExit(f"Banco não encontrado: {args.db}")
        url = f"sqlite:///{args.db}"
    else:
        url = args.db_url or settings.database.url

    engine = create_engine(url)

    registros, erros = ler_planilha(args.arquivo)
    if erros:
        print("Erros de formato na planilha:")
        for erro in erros:
            print(f"  - {erro}")
        print("\nNada foi gravado. Corrija a planilha e rode de novo.")
        return 1

    with engine.connect() as conexao:
        mudancas, faltantes, divergentes = comparar(conexao, registros)
        encontrados = len(registros) - len(faltantes)
        limite_divergencia = max(5, int(0.05 * max(1, encontrados)))
        if (
            divergentes
            and len(divergentes) > limite_divergencia
            and not args.permitir_nomes_divergentes
        ):
            print(
                "ABORTADO: os nomes do banco não batem com a planilha em "
                f"{len(divergentes)} de {encontrados} IDs encontrados."
            )
            print("Isso indica que a planilha veio de outro banco/catálogo.")
            for produto_id, nome_planilha, nome_banco in divergentes[:10]:
                print(
                    f"  ID {produto_id}: planilha={nome_planilha!r} "
                    f"banco={nome_banco!r}"
                )
            if len(divergentes) > 10:
                print(f"  ... e mais {len(divergentes) - 10}.")
            print(
                "\nConfira a URL/arquivo do banco. Se as diferenças forem "
                "renomeações esperadas, rode de novo com "
                "--permitir-nomes-divergentes."
            )
            return 2

        if divergentes:
            print(
                f"Atenção: {len(divergentes)} nome(s) divergente(s), "
                "dentro do limite:"
            )
            for produto_id, nome_planilha, nome_banco in divergentes[:10]:
                print(
                    f"  ID {produto_id}: planilha={nome_planilha!r} "
                    f"banco={nome_banco!r}"
                )
            print()

        if not mudancas and not faltantes:
            print("Nada a fazer: o banco já está igual à planilha.")
            return 0

        print(f"Planilha: {args.arquivo}")
        print(f"Banco:    {url_sem_senha(url)}")
        print(f"Linhas com NCM: {len(registros)}")
        print(f"IDs não encontrados no banco: {len(faltantes)}")
        if faltantes:
            print("  " + ", ".join(str(item["id"]) for item in faltantes[:30]))

        por_campo: Dict[str, int] = {}
        for mudanca in mudancas:
            for campo in mudanca["campos"]:
                por_campo[campo] = por_campo.get(campo, 0) + 1
        print(f"Produtos com alguma mudança: {len(mudancas)}")
        print(
            "Mudanças por campo: "
            + ", ".join(f"{campo}={qtd}" for campo, qtd in sorted(por_campo.items()))
        )
        print()

        for mudanca in mudancas[: args.limite]:
            detalhes = "; ".join(
                f"{campo}: {antes or '-'} -> {depois or '-'}"
                for campo, (antes, depois) in mudanca["campos"].items()
            )
            print(f"  {mudanca['id']:>4} {mudanca['nome'][:38]:<38} {detalhes}")
        if len(mudancas) > args.limite:
            print(f"  ... e mais {len(mudancas) - args.limite} produtos.")

        relatorio = args.relatorio or args.arquivo.with_suffix(".diff.csv")
        salvar_relatorio(relatorio, mudancas)
        print(f"\nDiff completo: {relatorio}")

    if not args.aplicar:
        print("\nDRY-RUN: nada foi gravado. Use --aplicar para atualizar o banco.")
        return 0

    backup = fazer_backup(engine, args.backup_feito)
    with engine.begin() as conexao:
        aplicar(conexao, mudancas)

    print("\nBanco atualizado.")
    if backup:
        print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
