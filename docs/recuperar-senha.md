# Recuperar senha (procedimento do administrador)

Não existe recuperação self-service: o botão "Esqueci minha senha" orienta
a falar com o administrador. Este roteiro é para quem tem acesso ao servidor.
No futuro, um painel admin web substitui este processo
(depende do item de usuários/permissões do roadmap).

## Gerar o hash da nova senha

Em qualquer máquina com o `venv` do projeto:

```bash
venv/bin/python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('NOVA-SENHA-AQUI'))"
```

Saída parecida com (guarde o valor completo, de uma linha só):

```text
scrypt:32768:8:1$abc123...$def456...
```

## SQLite (dev / VPS antiga)

```bash
sqlite3 billflux.db "UPDATE user SET password_hash = '<HASH>' WHERE username = 'coqueiral';"
sqlite3 billflux.db "SELECT id, username FROM user WHERE username = 'coqueiral';"
```

## PostgreSQL (produção)

```bash
psql "$POSTGRES_DB" -c "UPDATE \"user\" SET password_hash = '<HASH>' WHERE username = 'coqueiral';"
psql "$POSTGRES_DB" -c 'SELECT id, username FROM "user";'
```

## Depois de trocar

1. Não precisa reiniciar nada (a senha é lida do banco a cada login).
2. Teste o login com a nova senha.
3. Avise o usuário e peça para ele trocar em seguida, se houver essa rotina.

## Avisos

- Quem tem acesso à VPS consegue redefinir **qualquer** senha por este
  método — mais um motivo para concluir usuários/permissões no futuro.
- Nunca commite hashes reais nem compartilhe o `.env` de produção.
