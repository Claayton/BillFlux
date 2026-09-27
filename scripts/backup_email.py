#!/usr/bin/env python3
"""Envia o backup do BeeFlux por email (conta Gmail dedicada).

Fluxo:
  1. Roda `pg_dump` (texto) do Postgres de produção.
  2. Compacta com gzip + data no nome.
  3. Anexa o `.env` de produção (sem ele o restore não sobe).
  4. Envia via SMTP do Gmail com senha de app.
  5. Trava de tamanho (~20MB): acima disso pula o envio e falha,
     sinal de que o banco cresceu além do que email comporta.

Uso na VPS (com o .env de produção carregado)::
    BACKUP_EMAIL_TO=beeflux.backup@gmail.com \\
    BACKUP_EMAIL_USER=beeflux.backup@gmail.com \\
    BACKUP_EMAIL_APP_PASSWORD=<senha-de-app> \\
    python3 scripts/backup_email.py

Teste sem enviar nada (só monta o email e valida tudo)::
    python3 scripts/backup_email.py --dry-run

Somente stdlib — sem dependências novas.
"""

from __future__ import annotations

import argparse
import gzip
import os
import shutil
import smtplib
import subprocess
import sys
import tempfile
from datetime import date
from email.message import EmailMessage
from pathlib import Path
from typing import NoReturn

# Limite do Gmail: 25MB por mensagem. Trava com folga.
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

ROOT = Path(__file__).resolve().parent.parent


def fail(message: str, code: int = 1) -> NoReturn:
    print(f"backup_email: ERRO: {message}", file=sys.stderr)
    raise SystemExit(code)


def load_dotenv(env_path: Path) -> None:
    """Carrega o .env como dados (nunca executa nada).

    Parser mínimo e seguro: ignora linhas vazias/comentários, aceita
    prefixo `export`, aspas simples/duplas e valores com `=` ou `#`.
    Variáveis já presentes no ambiente têm prioridade (não sobrescreve).
    """
    try:
        text = env_path.read_text(encoding="utf-8")
    except OSError:
        return
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].lstrip()
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        if not key or not key.replace("_", "").isalnum() or key[0].isdigit():
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def run_pg_dump() -> bytes:
    """Gera o dump texto do Postgres de produção."""
    user = os.environ.get("POSTGRES_USER", "billflux")
    dbname = os.environ.get("POSTGRES_DB", "billflux")
    password = os.environ.get("POSTGRES_PASSWORD")
    if not password:
        fail("POSTGRES_PASSWORD não definido (carregue o .env de produção).")

    pg_dump = shutil.which("pg_dump")
    if pg_dump:
        cmd = [pg_dump, "-h", "localhost", "-U", user, "-d", dbname, "--no-password"]
    else:
        docker = shutil.which("docker")
        if not docker:
            fail("nem pg_dump nem docker encontrados no PATH.")
        cmd = [
            docker,
            "compose",
            "exec",
            "-T",
            "postgres",
            "pg_dump",
            "-U",
            user,
            "-d",
            dbname,
            "--no-password",
        ]
    env = {**os.environ, "PGPASSWORD": password}
    try:
        proc = subprocess.run(cmd, env=env, capture_output=True, timeout=600, cwd=ROOT)
    except subprocess.TimeoutExpired:
        fail("pg_dump excedeu 10 minutos.")
    if proc.returncode != 0:
        fail(f"pg_dump falhou: {proc.stderr.decode(errors='replace')[:300]}")
    if not proc.stdout:
        fail("pg_dump retornou vazio.")
    return proc.stdout


def build_email(
    dump_gz: bytes, dump_name: str, env_bytes: bytes | None
) -> EmailMessage:
    """Monta a mensagem (pura, sem enviar) — usada pelo --dry-run."""
    sender = os.environ.get("BACKUP_EMAIL_USER")
    recipient = os.environ.get("BACKUP_EMAIL_TO")
    if not sender or not recipient:
        fail("BACKUP_EMAIL_USER e BACKUP_EMAIL_TO precisam estar definidos.")
    if "@" not in sender or "@" not in recipient:
        fail("endereço de email inválido em BACKUP_EMAIL_USER/TO.")

    total = len(dump_gz) + (len(env_bytes) if env_bytes else 0)
    if total > MAX_ATTACHMENT_BYTES:
        fail(
            f"anexos com {total / 1024 / 1024:.1f}MB excedem o limite de "
            f"{MAX_ATTACHMENT_BYTES / 1024 / 1024:.0f}MB — hora de migrar para storage."
        )

    today = date.today().isoformat()
    msg = EmailMessage()
    msg["Subject"] = f"[BeeFlux backup] {today}"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(
        "Backup automático do BeeFlux.\n\n"
        f"Data: {today}\n"
        f"Dump: {dump_name} ({len(dump_gz) / 1024:.0f} KB comprimido)\n"
        ".env de produção anexado (necessário para restaurar).\n"
    )
    msg.add_attachment(
        dump_gz, maintype="application", subtype="gzip", filename=dump_name
    )
    if env_bytes:
        msg.add_attachment(
            env_bytes, maintype="text", subtype="plain", filename=".env.producao"
        )
    return msg


def send_email(msg: EmailMessage) -> None:
    """Envia via SMTP do Gmail com senha de app."""
    sender = os.environ["BACKUP_EMAIL_USER"]
    app_password = os.environ.get("BACKUP_EMAIL_APP_PASSWORD")
    if not app_password:
        fail("BACKUP_EMAIL_APP_PASSWORD não definido.")
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=120) as smtp:
            smtp.starttls()
            smtp.login(sender, app_password)
            smtp.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        fail(f"falha no envio SMTP: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup do BeeFlux por email.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="monta o email e valida tudo sem enviar.",
    )
    args = parser.parse_args()

    # .env da raiz do projeto (funciona de qualquer cwd; ambiente vence).
    load_dotenv(ROOT / ".env")

    dump_sql = run_pg_dump()
    with tempfile.NamedTemporaryFile(suffix=".sql.gz", delete=False) as tmp:
        # gzip.GzipFile (não gzip.open): mtime existe em qualquer versão.
        with gzip.GzipFile(tmp.name, "wb", compresslevel=9, mtime=0) as gz:
            gz.write(dump_sql)
        dump_path = Path(tmp.name)

    env_path = ROOT / ".env"
    env_bytes = env_path.read_bytes() if env_path.exists() else None
    if env_bytes is None:
        print("backup_email: AVISO: .env não encontrado, seguindo sem ele.")

    try:
        dump_name = f"beeflux-{date.today().isoformat()}.sql.gz"
        msg = build_email(dump_path.read_bytes(), dump_name, env_bytes)
    finally:
        dump_path.unlink(missing_ok=True)

    if args.dry_run:
        print(
            f"backup_email: DRY-RUN OK — email '{msg['Subject']}' montado "
            f"para {msg['To']} ({len(bytes(msg)) / 1024:.0f} KB, nada enviado)."
        )
        return

    send_email(msg)
    print(f"backup_email: enviado '{msg['Subject']}' para {msg['To']}.")


if __name__ == "__main__":
    main()
