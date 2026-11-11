#!/usr/bin/env python3
"""Reenvia as NFC-e pendentes do BeeFlux (cron/systemd).

Uso na VPS (com o .env de produção carregado)::

    set -a && . ./.env && set +a
    venv/bin/python scripts/fiscal_reenviar.py

Agendamento sugerido (a cada 5 minutos)::

    */5 * * * * cd /caminho/do/BillFlux && set -a && . ./.env && set +a \
      && venv/bin/python scripts/fiscal_reenviar.py >> /var/log/beeflux-fiscal.log 2>&1

Opções:

    --limit N    máximo de notas processadas (padrão 50)
    --force      ignora o intervalo de backoff e o auto_retry
    --dry-run    apenas lista as pendentes, sem chamar o provedor
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from billflux.services.fiscal import FiscalService  # noqa: E402


def _describe(document) -> str:
    error = (document.error_message or "").strip().replace("\n", " ")
    if len(error) > 120:
        error = error[:117] + "..."
    return (
        f"nota {document.id} | venda {document.order_id} | "
        f"{document.status} | tentativas {document.retry_count}"
        + (f" | {error}" if error else "")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    limit = max(1, min(args.limit, 200))
    service = FiscalService()

    if args.dry_run:
        documents = service.listar_pendentes()
        print(f"{len(documents)} nota(s) pendente(s)")
        for document in documents[:limit]:
            print(_describe(document))
        return 0

    missing = service.config.missing
    if missing:
        print(
            "fiscal_reenviar: configuração incompleta: " + ", ".join(missing),
            file=sys.stderr,
        )
        return 2

    summary = service.reemitir_pendentes(limit=limit, force=args.force)
    print(
        "fiscal_reenviar: "
        f"processadas={summary['processed']} "
        f"autorizadas={summary['authorized']} "
        f"pendentes={summary['pending']} "
        f"ignoradas={summary['skipped']}"
    )
    for detail in summary["documents"]:
        print(
            f"  nota {detail['id']} | venda {detail['order_id']} | "
            f"{detail['status']}"
            + (f" | {detail['error']}" if detail.get("error") else "")
        )

    return 0 if summary["pending"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
