# Backup por email (conta Gmail dedicada)

Backup diário, sem custo e sem infra nova: `pg_dump` → `gzip` → email.
Script: `scripts/backup_email.py` (só stdlib).

## Pré-requisitos (uma vez)

1. Conta Gmail **dedicada** ao backup, com 2FA ativo + email/telefone de recuperação.
2. Senha de app: Google Conta > Segurança > Senhas de app (guarde em local seguro, aparece uma vez só).
3. No `.env` da VPS:
   ```bash
   BACKUP_EMAIL_TO=beeflux.backup@gmail.com
   BACKUP_EMAIL_USER=beeflux.backup@gmail.com
   BACKUP_EMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
   ```
4. No Gmail da conta de backup: filtro `subject:"[BeeFlux backup]"` → aplicar label + arquivar.

## Teste inicial (na VPS, com o .env carregado)

```bash
python3 scripts/backup_email.py --dry-run   # monta tudo, não envia
python3 scripts/backup_email.py             # envia de verdade
```

Confirme o email chegando com os 2 anexos (`beeflux-AAAA-MM-DD.sql.gz` + `.env.producao`).

## Cron diário (na VPS, após o dump atual)

```cron
30 3 * * * cd /caminho/do/BillFlux && set -a && . ./.env && set +a && python3 scripts/backup_email.py >> /var/log/beeflux-backup.log 2>&1
```

## Teste de restore (fazer uma vez, ~30 min)

```bash
# 1. Baixe o .sql.gz mais recente do email
# 2. Suba um banco limpo e importe:
createdb beeflux_restore
gunzip -c beeflux-AAAA-MM-DD.sql.gz | psql beeflux_restore
# 3. Confira tabelas e contagem de vendas:
psql beeflux_restore -c "SELECT count(*) FROM sale;"
```

Se abrir e os números baterem, o backup presta.

## Limites

- Anexos acima de ~20MB abortam o envio (o script avisa) — sinal de migrar para storage.
- O `.env` de produção viaja junto (necessário para restaurar). Protegido pelo 2FA da conta.
