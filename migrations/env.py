"""Configuração do Alembic para o BeeFlux.

A URL do banco é lida da aplicação (``settings.database.url`` →
``BILLFLUX_DATABASE__URL``), então dev (SQLite) e produção (Postgres) usam a
mesma configuração. Importar ``billflux.infra.config.database`` registra todas
as entidades em ``SQLModel.metadata`` (usado pelo autogenerate).
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

import billflux.infra.config.database  # noqa: F401  (registra as entidades)
from billflux.config import settings

config = context.config

# Interpreta o arquivo de config para o logging (alembic.ini).
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL da aplicação. '%' precisa ser escapado (ConfigParser lê o .ini).
_database_url = str(settings.database.url)
config.set_main_option("sqlalchemy.url", _database_url.replace("%", "%%"))

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Gera o SQL sem conectar ao banco (``alembic upgrade --sql``)."""

    context.configure(
        url=_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        render_as_batch=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Aplica as migrações conectando ao banco."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
