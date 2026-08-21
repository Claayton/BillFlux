# ---------- Stage 1: build do SPA (Vue 3 + Vite) ----------
FROM node:20-alpine AS frontend

WORKDIR /workspace/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
# Saída (vite.config.js, outDir): ../billflux/static/app -> /workspace/billflux/static/app
RUN npm run build

# ---------- Stage 2: runtime Python (API JSON + SPA) ----------
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY billflux/ ./billflux/
COPY run.py settings.toml ./
COPY --from=frontend /workspace/billflux/static/app ./billflux/static/app

RUN useradd -m appuser && mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]
