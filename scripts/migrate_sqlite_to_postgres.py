"""Migra os dados do SQLite (billflux.db) para o PostgreSQL.

Uso (dentro do container da API, com BILLFLUX_DATABASE__URL já apontando
para o PostgreSQL):

    python scripts/migrate_sqlite_to_postgres.py [caminho/para/billflux.db]

O schema no Postgres é criado/atualizado via ``create_db()`` da aplicação.
Antes de copiar, as triggers (FK) são desabilitadas para ignorar a ordem de
inserção; ao final, as sequences das chaves primárias são reiniciadas.
"""

import os
import sys
from datetime import date, datetime
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, inspect, text  # noqa: E402

SQLITE_PATH = sys.argv[1] if len(sys.argv) > 1 else "billflux.db"

_DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
)


def _coerce(value, column_type):
    """Converte um valor do SQLite para o tipo Python equivalente do Postgres."""
    if value is None:
        return None
    if isinstance(value, str) and value == "":
        return None
    ctype = str(column_type or "").upper()

    if "BOOL" in ctype:
        if isinstance(value, bool):
            return value
        return bool(value)

    if "DATETIME" in ctype:
        if isinstance(value, datetime):
            return value
        raw = str(value)
        for fmt in _DATETIME_FORMATS:
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        return raw

    if "DATE" in ctype:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()

    if "NUMERIC" in ctype or "DECIMAL" in ctype:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    return value


def main():
    postgres_url = os.environ.get("BILLFLUX_DATABASE__URL")
    if not postgres_url or not postgres_url.startswith("postgresql"):
        sys.exit(
            "Defina BILLFLUX_DATABASE__URL apontando para o PostgreSQL "
            "(ex.: postgresql+psycopg2://user:pass@host:5432/billflux)."
        )

    # Importa após validar a URL: o engine da aplicação é criado no import.
    from billflux.infra.config.database import create_db, engine as pg_engine
    from billflux.infra.entities.user import User  # noqa: F401 (registra a tabela)

    print(f"Origem (SQLite): {SQLITE_PATH}")
    print(f"Destino (Postgres): {postgres_url.split('@')[-1]}")

    create_db()

    sqlite_engine = create_engine(f"sqlite:///{SQLITE_PATH}")
    sqlite_inspector = inspect(sqlite_engine)
    pg_inspector = inspect(pg_engine)

    tables = sqlite_inspector.get_table_names()
    pg_tables = set(pg_inspector.get_table_names())

    with pg_engine.begin() as pg_conn:
        for table in tables:
            if table in pg_tables:
                pg_conn.execute(text(f'ALTER TABLE "{table}" DISABLE TRIGGER ALL'))

        with sqlite_engine.connect() as sqlite_conn:
            for table in tables:
                if table not in pg_tables:
                    print(f"pular '{table}': não existe no Postgres")
                    continue
                columns = sqlite_inspector.get_columns(table)
                col_names = [c["name"] for c in columns]
                col_types = {c["name"]: c.get("type") for c in columns}
                rows = sqlite_conn.execute(text(f'SELECT * FROM "{table}"')).fetchall()
                if not rows:
                    continue
                placeholders = ", ".join(f":{name}" for name in col_names)
                insert_sql = (
                    f'INSERT INTO "{table}" ({", ".join(col_names)}) '
                    f"VALUES ({placeholders})"
                )
                for row in rows:
                    values = {
                        name: _coerce(row[idx], col_types[name])
                        for idx, name in enumerate(col_names)
                    }
                    pg_conn.execute(text(insert_sql), values)
                print(f"{table}: {len(rows)} linha(s)")

        for table in tables:
            if table in pg_tables:
                pg_conn.execute(text(f'ALTER TABLE "{table}" ENABLE TRIGGER ALL'))

    # Reinicia as sequences das chaves primárias.
    with pg_engine.begin() as pg_conn:
        for table in tables:
            if table not in pg_tables:
                continue
            pks = sqlite_inspector.get_pk_constraint(table)["constrained_columns"]
            if not pks:
                continue
            pk = pks[0]
            row = pg_conn.execute(text(f'SELECT MAX("{pk}") FROM "{table}"')).fetchone()
            if row and row[0] is not None:
                seq = pg_conn.execute(
                    text("SELECT pg_get_serial_sequence(:table, :col)"),
                    {"table": table, "col": pk},
                ).fetchone()[0]
                if seq:
                    pg_conn.execute(
                        text(f"SELECT setval('{seq}', :val)"), {"val": row[0]}
                    )
                    print(f"sequence {seq} -> {row[0]}")

    print("Migração concluída.")


if __name__ == "__main__":
    main()
