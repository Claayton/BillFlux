# Módulo Fiscal — NFC-e (Brasil NFe)

> Projeto da emissão de **NFC-e (modelo 65)** integrada ao PDV do BeeFlux.
> Provedor inicial: **Brasil NFe**, atrás de uma camada plugável.
> Estado: **Fase 2 — backend de emissão/cancelamento/reenvio concluído**.
> Os botões do PDV e a tela de pendências entram depois da homologação.

## 1. Decisões fechadas

| Tema | Decisão |
|---|---|
| UF | Paraná (PR) |
| Regime | Simples Nacional (`CRT = 1`) |
| Documento | **Somente NFC-e (modelo 65)** por enquanto; NF-e fica para depois |
| Provedor | **Brasil NFe** (`https://api.brasilnfe.com.br`) |
| Troca de provedor | Camada `FiscalProvider` (interface) + factory; provedor gravado por nota |
| Emissão | Botão **"Emitir nota"** direto no modal de pagamento do PDV |
| Sem nota | Botão **"Finalizar"** fecha a venda sem nota |
| Falha na emissão | A venda **fecha normalmente** e a nota fica **pendente** (reenvio) |
| Aviso | Banner na tela inicial enquanto houver nota pendente |
| Emitir depois | Permitido pela tela de Vendas; a nota sai com a **data/hora da emissão** |
| CPF/CNPJ | Opcional; com cliente selecionado preenche; sem cliente = consumidor não identificado |
| Fiado | Emite com `TipoPagamento = 99 (outros)` e mostra aviso |
| Desconto | Vai como desconto na nota (`vDesc`) |
| Pagamento dividido | Uma linha de pagamento por forma |
| NCM | Preenchido automaticamente pelas NF-es de compra; **sem NCM bloqueia a emissão** (o CFOP da compra não é copiado: é o CFOP de saída do fornecedor) |
| Padrões Simples | `CSOSN 102`, `origem 0`, `CFOP 5102` (ou `5405` com ST) — editáveis |
| Pendências | Tela/filtro "Pendências fiscais" com o que falta por produto |
| Token | Variável de ambiente `BRASILNFE_TOKEN` (nunca no banco) |
| Impressão | Configurável: **térmico 80mm com QR** / **PDF do DANFE** / **não imprimir** |
| Cancelamento | Cancelar a venda **cancela a nota junto**, exigindo justificativa |
| Fora do prazo | Se a SEFAZ recusar o cancelamento, **bloqueia** o cancelamento da venda |
| Reenvio | Automático (backoff) **+** botão manual |
| Escopo | Somente vendas do **PDV** (vendas avulsas ficam para depois) |
| Numeração | Gerenciada pelo provedor; série/número atuais serão informados na migração |

## 2. Arquitetura

```
billflux/services/fiscal/
  __init__.py
  base.py        # FiscalProvider (ABC) + DTOs + status
  config.py      # settings + BRASILNFE_TOKEN → FiscalConfig
  brasilnfe.py   # adapter Brasil NFe (JSON, header Token, urllib)
  builder.py     # venda do PDV → FiscalRequest (NCM, CFOP, pagamentos...)
  factory.py     # get_provider() a partir de fiscal.provider
  service.py     # emitir/reenviar/cancelar/XML/DANFE + fila de pendentes

billflux/infra/entities/fiscal_document.py
billflux/domain/models/fiscal_documents.py
billflux/infra/repository/fiscal_document_repository.py
migrations/versions/e5f6a7b8c9d0_fiscal_document.py
```

O restante do sistema (PDV, Vendas, Config) conversa **somente** com o
`FiscalService`; o serviço conversa com a interface `FiscalProvider`.
Trocar de provedor = novo adapter + `FISCAL_PROVIDER=outro`.

### Interface

```python
class FiscalProvider(ABC):
    def emit(request: FiscalRequest) -> FiscalResult: ...
    def cancel(access_key: str, justification: str) -> FiscalCancelResult: ...
    def query(access_key: str = "", identifier: str = "") -> FiscalQueryResult: ...
    def download_xml(access_key: str) -> bytes: ...
    def download_danfe(access_key: str) -> bytes: ...
    def test_connection() -> FiscalConnectionResult: ...
```

### Configuração

- `FISCAL_PROVIDER` (env, padrão `brasilnfe`)
- `BRASILNFE_TOKEN` (env, segredo; nunca no banco)
- `company.cnpj` (settings) — CNPJ do emitente
- `fiscal.environment` — `homologacao` | `producao`
- `fiscal.crt` — `1` (Simples), `3` (Normal)
- `fiscal.ie` — inscrição estadual
- `fiscal.print_mode` — `thermal` | `pdf` | `none`
- `fiscal.auto_retry` — `true` | `false`
- `fiscal.nfce_series` / `fiscal.nfce_last_number` — referência para migração
  (a emissão atual omite `Serie`/`Numero`/`Lote` e deixa o provedor numerar)

## 3. Modelo de dados

### `product` (novas colunas)

| Coluna | Tipo | Observação |
|---|---|---|
| `ncm` | texto(8) | obrigatório para emitir |
| `cest` | texto(7) | só quando houver ST |
| `cfop` | texto(4) | padrão `5102` / `5405` |
| `csosn` | texto(3) | Simples (padrão `102`) |
| `cst` | texto(2) | Regime Normal (opcional) |
| `origem` | inteiro | 0 = nacional |
| `fiscal_unit` | texto(6) | unidade comercial (padrão `UN`) |

### `purchase_item` (novas colunas)

`ncm` e `cfop` — capturados do XML da NF-e de compra e usados para
**preencher o cadastro fiscal do produto** no lançamento da compra.

### `fiscal_document` (Fase 2)

| Coluna | Observação |
|---|---|
| `id` | PK |
| `order_id` | venda do PDV (unique: 1 nota por venda) |
| `provider` | `brasilnfe` etc. — preserva o histórico na troca |
| `model` | `65` |
| `environment` | homologação/produção |
| `status` | `pendente`, `pendente_autorizacao`, `autorizada`, `rejeitada`, `cancelada`, `denegada` |
| `series`, `number` | retorno do provedor |
| `access_key` | chave de 44 dígitos |
| `protocol` | protocolo de autorização |
| `xml` | XML autorizado (texto) |
| `danfe` | PDF/DANFE em base64 (opcional) |
| `qr_code_url` | URL do QR Code |
| `error_code`, `error_message` | rejeição/configuração |
| `retry_count`, `next_retry_at` | fila de reenvio (backoff) |
| `created_at`, `updated_at`, `authorized_at`, `cancelled_at`, `cancel_reason` | auditoria |

`pendente_autorizacao` cobre a **contingência automática da NFC-e**
(`tpEmis=9`): a nota já foi registrada, mas o protocolo ainda não chegou.
Ela **não** deve aparecer como erro no banner.

## 4. Fluxo de emissão

```
POST /api/fiscal/emitir {order_id}
  → FiscalService.emitir(order_id)
      ├─ valida venda (existe? não cancelada?)
      ├─ cria/reaproveita fiscal_document (status pendente)
      ├─ monta FiscalRequest (NCM, CFOP, CSOSN, pagamentos, cliente)
      │    └─ NCM ausente → pendente (provedor não é chamado)
      ├─ provider.emit()
      │    ├─ autorizada            → grava chave/protocolo/XML/DANFE
      │    ├─ pendente_autorizacao  → contingência; consulta depois
      │    ├─ rejeitada/denegada    → grava erro da SEFAZ
      │    └─ falha de rede         → pendente + retry_count/backoff
      └─ devolve {ok, status, message, document}
```

No PDV (quando a UI entrar), o botão **"Emitir nota"** fecha a venda primeiro
e chama o mesmo serviço; **"Finalizar"** fecha sem criar `fiscal_document`.

### Regras

1. **Nunca perder venda por causa de nota**: erro do provedor não desfaz a venda.
2. **Idempotência**: uma nota por `order_id` (unique no banco). O
   `IdentificadorInterno` é `VENDA-<order_id>`; antes de reenviar, o serviço
   consulta o provedor para não duplicar (timeout, resposta perdida etc.).
3. **Sem NCM**: bloqueia antes de chamar o provedor e mantém a nota pendente
   com a lista de produtos. CFOP/CSOSN/origem/unidade têm padrões.
4. **Configuração incompleta**: token/CNPJ/IE ausentes deixam a nota pendente
   com mensagem clara; depois de corrigir, o reenvio funciona.
5. **Cancelamento**: justificativa de 15 a 1000 caracteres; tenta cancelar na
   SEFAZ **antes** de cancelar a venda. Se a SEFAZ recusar (fora do prazo de
   30 min da NFC-e), a venda **não** é cancelada e o usuário é orientado.
6. **Emitir depois**: a NFC-e usa a data/hora da emissão (não retroage).
7. **Contingência**: o provedor cobre SEFAZ fora (NFC-e automática); o Agente
   local cobre internet fora (opcional, sem custo no plano).
8. **Reenvio**: `retry_count` + `next_retry_at` com backoff de 5 a 60 minutos.
   O botão manual ignora o agendamento; o script `scripts/fiscal_reenviar.py`
   roda no cron/systemd e respeita `fiscal.auto_retry`.

### Bebidas sujeitas a ST (Paraná)

Cervejas, refrigerantes, energéticos, isotônicos e **água mineral** estão no
regime de substituição tributária no PR (Decreto 9.673/2021, água desde
01/03/2022). Para esses produtos: **CSOSN 500**, **CFOP 5405** e o **CEST** do
Convênio ICMS 142/18.

| Produto | CEST |
|---|---|
| Refrigerante em PET | `03.010.01` |
| Refrigerante em lata | `03.010.02` |
| Refrigerante em vidro descartável | `03.010.00` |
| Demais refrigerantes | `03.011.00` |
| Energético em lata | `03.013.00` |
| Energético em PET | `03.013.01` |
| Energético em vidro | `03.013.02` |
| Água mineral em garrafa plástica descartável (500 ml a < 5 L) | `03.005.04` |

## 5. Endpoints (API)

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/fiscal/status` | Configuração atual + pendências + `ready` + `pending_documents` |
| `GET` | `/api/fiscal/pending-products` | Produtos ativos sem dados fiscais |
| `POST` | `/api/fiscal/emitir` | Emite/reaproveita a NFC-e de uma venda (`{"order_id": 1}`) |
| `POST` | `/api/fiscal/<id>/reenviar` | Reenvia uma nota pendente (consulta antes) |
| `POST` | `/api/fiscal/reenviar-pendentes` | Reenvio em lote (botão manual; `{"limit": 50}`) |
| `POST` | `/api/fiscal/<id>/cancelar` | Cancela com `{"justificativa": "..."}` |
| `GET` | `/api/fiscal/pendentes` | Notas pendentes + dados da venda (banner/tela) |
| `GET` | `/api/fiscal/vendas/<order_id>` | Situação fiscal de uma venda |
| `GET` | `/api/fiscal/<id>/xml` | Baixa o XML autorizado |
| `GET` | `/api/fiscal/<id>/danfe` | Baixa o DANFE (PDF ou HTML) |
| `POST` | `/api/fiscal/testar-conexao` | Consulta o status da SEFAZ (`107` = operação) |

### Reenvio automático

```bash
# cron a cada 5 minutos (com o .env carregado)
*/5 * * * * cd /caminho/do/BillFlux && set -a && . ./.env && set +a \
  && venv/bin/python scripts/fiscal_reenviar.py >> /var/log/beeflux-fiscal.log 2>&1
```

`--dry-run` lista as pendentes sem chamar o provedor; `--force` ignora o
`auto_retry` e o backoff. O script sai com código 1 se sobrar nota pendente.

## 6. Telas

- **Produtos → Dados → aba Fiscal**: NCM (obrigatório), CEST, CFOP, CSOSN/CST, origem, unidade. CFOP/CSOSN/origem/unidade usam padrão quando vazios.
- **Produtos**: badge "Sem NCM" e filtro **"Pendências fiscais"**.
- **Config → Fiscal**: provedor, ambiente, regime, IE, impressão, reenvio,
  série/último número, status do token e botão **"Testar conexão"**.
- **PDV → modal de pagamento**: **Finalizar** e **Emitir nota**.
- **Vendas**: badge por venda (`Sem nota`, `Pendente`, `Autorizada`, `Cancelada`),
  ações (emitir, reenviar, cancelar nota, XML/DANFE) e banner de pendências.

## 7. Checklist de homologação (Fase 2)

Backend já coberto por testes com **provedor fake** e testes de contrato do
adapter (payload/parse). O que falta depende do painel do Brasil NFe.

- [x] Camada `FiscalProvider` + adapter Brasil NFe
- [x] `fiscal_document` + migração
- [x] Emissão, reenvio (idempotente), cancelamento, XML/DANFE e status
- [x] Cancelamento da venda bloqueado quando a SEFAZ recusa
- [x] Testes de payload (fiado, desconto, pagamento dividido, CPF, GTIN)
- [x] Token de homologação no `.env`
- [x] Certificado A1 e-CNPJ cadastrado no painel do Brasil NFe
- [x] Emitente completo (CNPJ, IE, endereço, CRT)
- [x] Produtos de teste com NCM/CFOP/CSOSN
- [x] Botões **Finalizar / Emitir nota** no PDV e banner de pendências em Vendas
- [x] **CSC de homologação** cadastrado no painel do Brasil NFe (ID + CSC)
- [x] Situação fiscal por venda em Vendas (badge, emitir/reenviar, XML/DANFE,
  cancelar nota)
- [x] Emitir venda simples (1 item, dinheiro) — vendas #19 e #20 autorizadas
- [ ] Emitir com desconto
- [ ] Emitir com pagamento dividido
- [ ] Emitir com CPF e sem CPF
- [ ] Emitir fiado (`tPag 99`)
- [ ] Cancelar dentro do prazo (com justificativa)
- [ ] Reenviar nota pendente (simular queda)
- [ ] Reimprimir cupom/DANFE
- [x] Conferir XML e QR Code
- [ ] Migrar numeração (série/último número), se necessário
- [ ] Trocar `fiscal.environment` para `producao` e emitir 1 venda real

Contrato detalhado do provedor em [`docs/fiscal-brasilnfe.md`](fiscal-brasilnfe.md).

## 8. Fora de escopo (por enquanto)

- NF-e modelo 55 (vendas para empresa/interestadual)
- NFS-e
- Carta de correção
- Devolução fiscal
- SPED / SINTEGRA
- Emissão de vendas avulsas
- Agente local de contingência offline
