"""Migração idempotente do PostgreSQL de produção (BillFlux).

Prepara o schema das novas funcionalidades (comandas/tabs, fiado/receivables,
auditoria, movimentações de caixa e settings) sobre um banco que JÁ contém
dados reais, sem recriar nada e sem depender de ``SQLModel.metadata.create_all``.

Baseline: tag/estado ``prod-2026-10-01-predeploy`` (branch ``main``) -> HEAD.
Diff coberto: 7 tabelas novas + ``order_items.factor`` + ``uq_tab_number``.

Uso (dentro do container da API, com ``BILLFLUX_DATABASE__URL`` definido):

    python scripts/migrate_prod_pg.py            # aplica (idempotente)
    python scripts/migrate_prod_pg.py --validate # só valida, não altera nada

Garantias:
- apenas ``CREATE TABLE`` / ``ADD COLUMN`` / ``ADD CONSTRAINT`` — nunca ``DROP``;
- verifica a existência de cada estrutura antes de criá-la: rodar 2x não faz
  nada na 2ª vez (sem erro, sem duplicação);
- tudo dentro de uma transação; em qualquer erro faz rollback e sai com código 1;
- backfill explícito do único campo obrigatório novo: ``order_items.factor = 1``
  (os itens de pedido já existentes foram gravados em unidades-base).
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

# Reaproveita a engine da aplicação -> mesma resolução de BILLFLUX_DATABASE__URL.
from billflux.infra.config.database import engine  # noqa: E402

# ---------------------------------------------------------------------------
# DDL explícito, idêntico ao que o SQLAlchemy gera no dialeto PostgreSQL.
# A ordem respeita as dependências de FK entre as tabelas novas.
# ---------------------------------------------------------------------------
NEW_TABLES = [
    (
        "cash_movement",
        """
        CREATE TABLE cash_movement (
            id SERIAL NOT NULL,
            cash_register_id INTEGER NOT NULL,
            kind VARCHAR NOT NULL,
            amount FLOAT NOT NULL,
            obs VARCHAR,
            created_by VARCHAR NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(cash_register_id) REFERENCES cashregister (id)
        )
        """,
    ),
    (
        "receivable",
        """
        CREATE TABLE receivable (
            id SERIAL NOT NULL,
            order_id INTEGER,
            customer_id INTEGER NOT NULL,
            amount NUMERIC(10, 2) NOT NULL,
            paid_amount NUMERIC(10, 2) NOT NULL,
            cancelled BOOLEAN NOT NULL,
            obs VARCHAR,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(order_id) REFERENCES orders (id),
            FOREIGN KEY(customer_id) REFERENCES customer (id)
        )
        """,
    ),
    (
        "receivable_payment",
        """
        CREATE TABLE receivable_payment (
            id SERIAL NOT NULL,
            receivable_id INTEGER NOT NULL,
            method_id INTEGER,
            amount NUMERIC(10, 2) NOT NULL,
            cash_movement_id INTEGER,
            created_by VARCHAR NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(receivable_id) REFERENCES receivable (id),
            FOREIGN KEY(method_id) REFERENCES paymentmethod (id),
            FOREIGN KEY(cash_movement_id) REFERENCES cash_movement (id)
        )
        """,
    ),
    (
        "tab",
        """
        CREATE TABLE tab (
            id SERIAL NOT NULL,
            number INTEGER NOT NULL,
            identification VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            subtotal NUMERIC(10, 2) NOT NULL,
            discount NUMERIC(10, 2),
            total NUMERIC(10, 2) NOT NULL,
            order_id INTEGER,
            print_count INTEGER NOT NULL,
            opened_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            closed_at TIMESTAMP WITHOUT TIME ZONE,
            canceled_at TIMESTAMP WITHOUT TIME ZONE,
            opened_by VARCHAR,
            closed_by VARCHAR,
            canceled_by VARCHAR,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_tab_number UNIQUE (number),
            FOREIGN KEY(order_id) REFERENCES orders (id)
        )
        """,
    ),
    (
        "tab_item",
        """
        CREATE TABLE tab_item (
            id SERIAL NOT NULL,
            tab_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            unit_id INTEGER,
            name VARCHAR NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price NUMERIC(10, 2) NOT NULL,
            total NUMERIC(10, 2) NOT NULL,
            factor INTEGER NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(tab_id) REFERENCES tab (id),
            FOREIGN KEY(product_id) REFERENCES product (id)
        )
        """,
    ),
    (
        "audit_event",
        """
        CREATE TABLE audit_event (
            id SERIAL NOT NULL,
            actor VARCHAR NOT NULL,
            action VARCHAR NOT NULL,
            entity VARCHAR,
            entity_id INTEGER,
            details VARCHAR,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            PRIMARY KEY (id)
        )
        """,
    ),
    (
        "setting",
        """
        CREATE TABLE setting (
            key VARCHAR(120) NOT NULL,
            value VARCHAR,
            PRIMARY KEY (key)
        )
        """,
    ),
]

# Colunas novas em tabelas existentes.
# Regra de backfill: itens de pedido antigos foram gravados em unidades-base,
# logo ``factor = 1`` para todas as linhas existentes.
NEW_COLUMNS = [
    (
        "order_items",
        "factor",
        "ALTER TABLE order_items ADD COLUMN factor INTEGER NOT NULL DEFAULT 1",
    ),
]

# Constraints a garantir caso a tabela já exista sem elas.
ENSURE_CONSTRAINTS = [
    (
        "uq_tab_number",
        "tab",
        "ALTER TABLE tab ADD CONSTRAINT uq_tab_number UNIQUE (number)",
    ),
]


# ---------------------------------------------------------------------------
# Helpers de existência (sempre dentro da conexão corrente, sem cache)
# ---------------------------------------------------------------------------
def _table_exists(conn, name: str) -> bool:
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = current_schema() AND table_name = :n LIMIT 1"
        ),
        {"n": name},
    ).first()
    return row is not None


def _column_exists(conn, table: str, column: str) -> bool:
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = current_schema() "
            "AND table_name = :t AND column_name = :c LIMIT 1"
        ),
        {"t": table, "c": column},
    ).first()
    return row is not None


def _constraint_exists(conn, name: str, table: str) -> bool:
    row = conn.execute(
        text(
            "SELECT 1 FROM pg_constraint c "
            "JOIN pg_class t ON t.oid = c.conrelid "
            "WHERE c.conname = :n AND t.relname = :t LIMIT 1"
        ),
        {"n": name, "t": table},
    ).first()
    return row is not None


def _require_postgres() -> bool:
    if engine.dialect.name != "postgresql":
        print(
            f"ERRO: este script é só para PostgreSQL "
            f"(dialeto detectado: {engine.dialect.name})."
        )
        return False
    return True


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------
def apply_migration() -> int:
    if not _require_postgres():
        return 1

    applied: list[str] = []
    skipped: list[str] = []

    try:
        with engine.begin() as conn:
            for name, ddl in NEW_TABLES:
                if _table_exists(conn, name):
                    skipped.append(f"tabela {name} (já existe)")
                    continue
                conn.execute(text(ddl))
                applied.append(f"CREATE TABLE {name}")

            for table, column, ddl in NEW_COLUMNS:
                if _column_exists(conn, table, column):
                    skipped.append(f"coluna {table}.{column} (já existe)")
                    continue
                conn.execute(text(ddl))
                applied.append(
                    f"ADD COLUMN {table}.{column} "
                    f"(backfill = 1 para linhas existentes)"
                )

            for name, table, ddl in ENSURE_CONSTRAINTS:
                if _constraint_exists(conn, name, table):
                    skipped.append(f"constraint {name} em {table} (já existe)")
                    continue
                conn.execute(text(ddl))
                applied.append(f"ADD CONSTRAINT {name} em {table}")
    except Exception as exc:  # noqa: BLE001 - reporta e garante rollback
        print(f"\nERRO durante a migração: {exc}")
        print("Rollback executado — nenhuma alteração foi persistida.")
        return 1

    print("\n===== Migração concluída =====")
    print(f"\nAplicadas ({len(applied)}):")
    for line in applied or ["  (nenhuma)"]:
        print(f"  [aplicado]  {line}")
    print(f"\nIgnoradas por já existirem ({len(skipped)}):")
    for line in skipped or ["  (nenhuma)"]:
        print(f"  [ignorado]  {line}")
    print()
    return 0


# ---------------------------------------------------------------------------
# Validate (somente leitura)
# ---------------------------------------------------------------------------
def validate() -> int:
    if not _require_postgres():
        return 1

    problems: list[str] = []
    tables_ok = 0

    inspector = inspect(engine)
    db_tables = set(inspector.get_table_names())

    for name, table in sorted(SQLModel.metadata.tables.items()):
        if name not in db_tables:
            problems.append(f"tabela ausente: {name}")
            continue
        tables_ok += 1
        db_columns = {col["name"] for col in inspector.get_columns(name)}
        for column in table.columns:
            if column.name not in db_columns:
                problems.append(f"coluna ausente: {name}.{column.name}")

    with engine.connect() as conn:
        for cname, ctable, _ddl in ENSURE_CONSTRAINTS:
            if not _constraint_exists(conn, cname, ctable):
                problems.append(f"constraint ausente: {cname} em {ctable}")

    total = len(SQLModel.metadata.tables)
    print("\n===== Validação de schema (somente leitura) =====")
    print(f"Tabelas esperadas: {total} | presentes: {tables_ok}")
    if problems:
        print(f"\nPendências ({len(problems)}):")
        for line in problems:
            print(f"  [FALTA]  {line}")
        print("\nResultado: SCHEMA INCOMPLETO.")
        return 1

    print("\nResultado: SCHEMA OK — todas as tabelas, colunas e constraints existem.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Migração idempotente do PostgreSQL de produção (BillFlux)."
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="apenas valida o schema; não faz nenhuma alteração.",
    )
    args = parser.parse_args(argv)

    if args.validate:
        return validate()
    return apply_migration()


if __name__ == "__main__":
    sys.exit(main())
