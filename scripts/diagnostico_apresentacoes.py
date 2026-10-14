#!/usr/bin/env python3
"""Diagnóstico de apresentações de produto — SOMENTE LEITURA.

Roda contra o banco configurado em BILLFLUX_DATABASE__URL (ou o default do
settings.toml). Não altera nada: apenas lista anomalias e sugere os SQLs de
correção para você rodar manualmente se quiser.

Uso:
    BILLFLUX_DATABASE__URL="postgresql://..." venv/bin/python scripts/diagnostico_apresentacoes.py
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decimal import Decimal  # noqa: E402

from billflux.infra.config.database import get_session  # noqa: E402
from billflux.infra.entities.product import Product  # noqa: E402
from billflux.infra.entities.product_unit import (  # noqa: E402
    ProductUnit,
)
from sqlmodel import select  # noqa: E402


def fmt(v):
    return f"R$ {Decimal(v):.2f}" if v is not None else "—"


def main():
    session = get_session()
    try:
        products = session.exec(select(Product).order_by(Product.name)).all()
        units = session.exec(
            select(ProductUnit).order_by(ProductUnit.product_id, ProductUnit.name)
        ).all()
    finally:
        session.close()

    units_by_product = {}
    for u in units:
        units_by_product.setdefault(u.product_id, []).append(u)

    anomalies = 0
    print("== Diagnóstico de apresentações/produto (read-only) ==\n")
    for p in products:
        units_list = units_by_product.get(p.id, [])
        default1 = [u for u in units_list if u.is_default and (u.factor or 1) == 1]
        defaults = [u for u in units_list if u.is_default]
        packs = [u for u in units_list if (u.factor or 1) > 1]

        problems = []
        if default1:
            if Decimal(p.price) != Decimal(default1[0].price):
                problems.append(
                    f"preço-base diverge: product.price={fmt(p.price)} vs "
                    f"unidade padrão {default1[0].name}={fmt(default1[0].price)}"
                )
        else:
            problems.append("sem unidade padrão de fator 1")

        if len(defaults) > 1:
            problems.append(f"{len(defaults)} apresentações marcadas como padrão")
        if packs and any(u.is_default for u in packs):
            names = ", ".join(u.name for u in packs if u.is_default)
            problems.append(f"padrão com fator>1: {names}")

        if problems:
            anomalies += 1
            print(
                f"* Produto #{p.id} '{(p.name or '').strip()}' "
                f"(price={fmt(p.price)}, cost={fmt(p.cost)}, stock={p.stock_quantity})"
            )
            for problem in problems:
                print(f"    - {problem}")
            for u in units_list:
                marker = "PADRÃO" if u.is_default else "       "
                print(
                    f"      {marker} {u.name} (factor {u.factor}) "
                    f"price={fmt(u.price)}"
                )
            print()

    if anomalies:
        print(
            f"== {anomalies} produto(s) com anomalia. ==\n"
            "Sugestões (rode manualmente, decida o que é o certo p/ cada caso):\n"
            "# 1) Unidade padrão define o preço-base (recomendado p/ PDV):\n"
            "#    UPDATE product SET price = (SELECT pu.price FROM product_unit pu\n"
            "#        WHERE pu.product_id = product.id AND pu.is_default = true\n"
            "#        AND pu.factor = 1 LIMIT 1)\n"
            "#    WHERE id IN (SELECT product_id FROM product_unit WHERE is_default = true AND factor = 1);\n"
            "# 2) Corrigir múltiplas padrões: manter só a de fator 1.\n"
            "Depois, no sistema, reabra o PDV (recarregar) para ver os preços novos."
        )
    else:
        print("Nenhuma anomalia encontrada.")


if __name__ == "__main__":
    main()
