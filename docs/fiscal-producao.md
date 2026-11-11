# Ir para produção — NFC-e (Paraná, Simples Nacional)

Roteiro de go-live do módulo fiscal. Faça na ordem; cada bloco tem uma
verificação antes de seguir. **Nada aqui deve ser executado em produção sem
o backup do passo 1.**

> Contexto: provedor **Brasil NFe**, somente NFC-e (modelo 65), emitente
> CNPJ `68.596.191/0001-30` / IE `9125356572` / CRT `1`.

---

## 0. Decisões e pré-requisitos (com o contador)

- [ ] Confirmar **série** e **numeração inicial** da NFC-e de produção
      (hoje a homologação está em série 1; confirmar se produção começa em 1/1)
- [ ] Confirmar CFOP de venda interna (`5102`) e de ST (`5405`)
- [ ] Confirmar CSOSN (`102` geral, `500` para ST) e CST de PIS/COFINS
      (`49` no Simples)
- [ ] **CSC de produção** gerado no painel do Brasil NFe (o de homologação não
      serve)
- [ ] Certificado A1 e-CNPJ válido no painel (mesmo da homologação, se ainda
      válido)
- [ ] Janela de implantação fora do horário de pico

---

## 1. Backup e ensaio da migração

```bash
cd /caminho/do/BillFlux

# backup do Postgres de produção
docker compose -f docker-compose-prod.yml exec -T postgres \
  pg_dump -U "${POSTGRES_USER:-billflux}" "${POSTGRES_DB:-billflux}" \
  | gzip > "backup-pre-fiscal-$(date +%Y%m%d-%H%M).sql.gz"

# confira que o arquivo tem tamanho plausível
ls -lh backup-pre-fiscal-*.sql.gz
```

A migração `e5f6a7b8c9d0_fiscal_document` é **aditiva** (só cria a tabela
`fiscal_document` + índices). O container da API roda `alembic upgrade head`
sozinho no start.

- [ ] Ensaio (recomendado): restaure o backup num banco de teste e rode
      `alembic upgrade head` lá antes do deploy real
- [ ] **Nunca** sobrescrever `billflux.db` do dev nem apontar o `.env` de
      produção para o banco errado

---

## 2. Configuração do provedor e do emitente

No painel <https://api.brasilnfe.com.br>:

- [ ] Ambiente de **produção** selecionado
- [ ] Certificado A1 de produção cadastrado
- [ ] Emitente completo (CNPJ, IE, endereço, CRT `1`)
- [ ] CSC de produção cadastrado (ID + CSC)
- [ ] Confirmar a cota do plano para o volume da loja

No `.env` **do host** (nunca commitar):

```dotenv
BRASILNFE_TOKEN=<token de produção>
FISCAL_PROVIDER=brasilnfe
```

O `docker-compose-prod.yml` repassa essas variáveis para o container da API.

No app, **Config → Fiscal**:

- [ ] Ambiente = **produção**
- [ ] IE e CNPJ do emitente
- [ ] Série e último número conforme o contador
- [ ] Impressão (térmica/PDF) e reenvio automático
- [ ] **Testar conexão** (status `107` = serviço em operação)

---

## 3. Catálogo fiscal

A emissão **bloqueia** produto sem NCM ou com NCM fora da tabela vigente da
Siscomex — e nem chama a SEFAZ (evita a rejeição 778).

- [ ] Atualizar a tabela embutida antes do deploy:
      `venv/bin/python scripts/atualizar_ncm.py`
- [ ] Todos os produtos ativos com **NCM válido**
- [ ] Bebidas (cerveja, refrigerante, energético, isotônico, água mineral) com
      **CSOSN 500**, **CFOP 5405** e **CEST**
- [ ] `GET /api/fiscal/status` com `pending_products: 0` e `ready: true`

Como conferir:

```bash
# na tela Produtos, use o filtro "Pendências fiscais";
# ou via API (autenticado):
curl -s -b cookies.txt https://seu-dominio/api/fiscal/status
```

> Se o catálogo de produção ainda não tem NCM, cadastre pela **aba Fiscal** do
> produto (ou por script de importação). Não copie o banco do dev para
> produção.

### Importar a planilha fiscal revisada

Use `scripts/importar_catalogo_fiscal.py`. Ele casa pelo **ID**, valida
NCM/CEST/CFOP/CSOSN/CST/origem, altera **só campos fiscais** e, por padrão,
**não grava nada** (dry-run).

```bash
# 1. leve a planilha revisada para o servidor
scp catalogo-fiscal-preenchido-2026-11-11.xlsx usuario@servidor:/tmp/

# 2. dry-run dentro do container da API (usa BILLFLUX_DATABASE__URL)
docker compose -f docker-compose-prod.yml exec -T api \
  python scripts/importar_catalogo_fiscal.py \
  --arquivo /tmp/catalogo-fiscal-preenchido-2026-11-11.xlsx

# 3. confira o resumo e o diff; se os IDs/nomes não baterem, ele aborta

# 4. backup e aplicação
docker compose -f docker-compose-prod.yml exec -T postgres \
  pg_dump -U "${POSTGRES_USER:-billflux}" "${POSTGRES_DB:-billflux}" \
  | gzip > "backup-antes-fiscal-$(date +%Y%m%d-%H%M).sql.gz"

docker compose -f docker-compose-prod.yml exec -T api \
  python scripts/importar_catalogo_fiscal.py \
  --arquivo /tmp/catalogo-fiscal-preenchido-2026-11-11.xlsx \
  --aplicar --backup-feito
```

Depois, confira em **Produtos → Pendências fiscais** (ou
`GET /api/fiscal/status`) que sobrou só o esperado.

---

## 4. Deploy

```bash
cd /caminho/do/BillFlux

docker compose -f docker-compose-prod.yml up -d --build
docker compose -f docker-compose-prod.yml logs -f api
```

No log deve aparecer o `alembic upgrade head` concluindo sem erro.

- [ ] `docker compose ... ps` com `api`, `web` e `postgres` de pé
- [ ] `alembic current` mostrando `e5f6a7b8c9d0` (head)
- [ ] Token presente no container **sem imprimir o valor**:
      `docker compose -f docker-compose-prod.yml exec api sh -c 'test -n "$BRASILNFE_TOKEN" && echo token-ok'`
- [ ] `/api/fiscal/status` → `ready: true`
- [ ] Login e uma venda de teste **sem emitir** (botão **Finalizar**) seguem
      funcionando

---

## 5. Primeira venda real

- [ ] Venda simples (1 item, dinheiro, valor baixo) com **Emitir nota**
- [ ] Status **Autorizada**, chave com 44 dígitos e protocolo
- [ ] XML e DANFE baixam pela tela de Vendas
- [ ] QR Code abre a consulta da NFC-e no portal da SEFAZ-PR
- [ ] Se for só teste, **cancelar em até 30 min** com justificativa (≥ 15
      caracteres) — depois disso a SEFAZ recusa e a venda fica bloqueada
- [ ] Guardar XML/DANFE da primeira nota

---

## 6. Operação contínua

Reenvio automático das notas pendentes (a cada 5 minutos), rodando **dentro do
container** (o banco e o token estão lá):

```bash
*/5 * * * * cd /caminho/do/BillFlux && \
  docker compose -f docker-compose-prod.yml exec -T api \
  python scripts/fiscal_reenviar.py >> /var/log/beeflux-fiscal.log 2>&1
```

- [ ] Cron instalado e com o usuário no grupo `docker`
- [ ] `--dry-run` retornando 0 notas no dia seguinte
- [ ] Log rotacionado (`logrotate`) para não crescer sem limite
- [ ] Banner de pendências do Vendas conhecido pela equipe
- [ ] XMLs para a contabilidade: baixar pelo painel do Brasil NFe
      (Relatórios → “Download de arquivos por período”, incluir saídas,
      modelo 65, marcar **Contabilidade**)

---

## 7. Plano B / rollback

- **SEFAZ ou provedor fora**: a venda **fecha normalmente** e a nota fica
  pendente; o banner avisa e o reenvio resolve depois.
- **Erro no deploy**: a migração é aditiva; voltar a imagem anterior mantém a
  tabela `fiscal_document` (sem uso pelo código antigo). As notas emitidas
  continuam válidas — cancele na SEFAZ se necessário.
- **Restaurar backup**: só em último caso; notas já transmitidas não podem ser
  “desfeitas” por restauração de banco.
- **Nunca** rode `down -v` em produção (apaga o volume do Postgres).

---

## Checklist rápido (copiar/colar)

- [ ] Backup do Postgres
- [ ] CSC de produção no painel
- [ ] `BRASILNFE_TOKEN` no `.env` do host
- [ ] Ambiente = produção no app
- [ ] Série/numeração confirmadas com o contador
- [ ] NCM/CEST de todos os produtos ativos
- [ ] Deploy + `alembic upgrade head`
- [ ] `/api/fiscal/status` → `ready: true`
- [ ] Primeira venda real autorizada (XML/DANFE/QR conferidos)
- [ ] Cron do `fiscal_reenviar.py`
- [ ] Equipe treinada no banner e nos botões Finalizar/Emitir nota
