# ---------- API BillFlux (JSON only) ----------
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt gunicorn

COPY billflux/ ./billflux/
COPY run.py settings.toml ./
COPY scripts/ ./scripts/
COPY alembic.ini ./
COPY migrations/ ./migrations/
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

RUN useradd -m appuser && mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

# Aplica as migrações (alembic upgrade head) e sobe o gunicorn.
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]
