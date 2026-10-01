#!/bin/sh
set -e

# Aplica as migrações pendentes do Alembic antes de subir a API.
# A URL vem de BILLFLUX_DATABASE__URL (ver migrations/env.py).
alembic upgrade head

exec "$@"
