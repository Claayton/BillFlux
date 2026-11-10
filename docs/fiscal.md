# Módulo Fiscal — NFC-e (Brasil NFe)

> Projeto da emissão de **NFC-e (modelo 65)** integrada ao PDV do BeeFlux.
> Provedor inicial: **Brasil NFe**, atrás de uma camada plugável.
> Estado: **Fase 1 (cadastros e configuração) — sem emissão**.

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
| NCM | Preenchido automaticamente pelas NF-es de compra; **sem NCM bloqueia a emissão** |
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
  base.py        # FiscalProvider (ABC) + DTOs
  brasilnfe.py   # adapter Brasil NFe (JSON, header Token)
  factory.py     # get_provider() a partir de FISCAL_PROVIDER
```

O restante do sistema (PDV, Vendas, Config) conversa **somente** com a interface.
Trocar de provedor = novo adapter + `FISCAL_PROVIDER=outro`.

### Interface

```python
class FiscalProvider(ABC):
    def emitir(self, nota: NotaFiscal) -> RetornoEmissao: ...
    def cancelar(self, chave: str, justificativa: str) -> RetornoCancelamento: ...
    def consultar(self, chave: str) -> RetornoConsulta: ...
    def baixar_xml(self, chave: str) -> bytes: ...
    def baixar_danfe(self, chave: str) -> bytes: ...
    def testar_conexao(self) -> RetornoConexao: ...
```

### Configuração

- `FISCAL_PROVIDER` (env, padrão `brasilnfe`)
- `BRASILNFE_TOKEN` (env, segredo)
- `fiscal.environment` — `homologacao` | `producao`
- `fiscal.crt` — `1` (Simples), `3` (Normal)
- `fiscal.ie` — inscrição estadual
- `fiscal.print_mode` — `thermal` | `pdf` | `none`
- `fiscal.auto_retry` — `true` | `false`
- `fiscal.nfce_series` / `fiscal.nfce_last_number` — referência para migração

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
| `order_id` | venda do PDV (1 nota por venda) |
| `provider` | `brasilnfe` etc. — preserva o histórico na troca |
| `model` | `65` |
| `environment` | homologação/produção |
| `status` | `pendente`, `autorizada`, `rejeitada`, `cancelada`, `denegada` |
| `series`, `number` | retorno do provedor |
| `access_key` | chave de 44 dígitos |
| `protocol` | protocolo de autorização |
| `xml` | XML autorizado (texto) |
| `danfe_pdf` | PDF em base64 (opcional) |
| `qr_code_url` | URL do QR Code |
| `error_code`, `error_message` | rejeição |
| `retry_count`, `next_retry_at` | fila de reenvio |
| `created_at`, `authorized_at`, `cancelled_at`, `cancel_reason` | auditoria |

## 4. Fluxo do PDV

```
[Modal de pagamento]
  ├─ "Finalizar"  → fecha a venda (fiscal_status = sem_nota)
  └─ "Emitir nota" → fecha a venda + cria fiscal_document(pendente)
                      → chama provider.emitir()
                        ├─ sucesso → autorizada + imprime (print_mode)
                        └─ falha   → pendente + banner na tela inicial
```

### Regras

1. **Nunca perder venda por causa de nota**: erro do provedor não desfaz a venda.
2. **Idempotência**: uma nota por `order_id`; reenvio não duplica.
3. **Sem NCM**: bloqueia antes de chamar o provedor e lista os itens pendentes.
4. **Configuração incompleta**: bloqueia com mensagem clara (token/IE/CNPJ/regime).
5. **Cancelamento**: justificativa obrigatória; tenta cancelar na SEFAZ **antes**
   de cancelar a venda. Se a SEFAZ recusar (fora do prazo), a venda **não** é
   cancelada e o usuário é orientado.
6. **Emitir depois**: a NFC-e usa a data/hora da emissão (não retroage).
7. **Contingência**: o provedor cobre SEFAZ fora; o Agente local cobre internet
   fora (opcional, sem custo no plano).

## 5. Endpoints (API)

| Método | Rota | Fase | Descrição |
|---|---|---|---|
| `GET` | `/api/fiscal/status` | 1 | Configuração atual + pendências + `ready` |
| `POST` | `/api/fiscal/emitir` | 2 | Emite a NFC-e de um pedido |
| `POST` | `/api/fiscal/<id>/reenviar` | 2 | Reenvia nota pendente |
| `POST` | `/api/fiscal/<id>/cancelar` | 2 | Cancela com justificativa |
| `GET` | `/api/fiscal/<id>/xml` | 2 | Baixa o XML |
| `GET` | `/api/fiscal/<id>/danfe` | 2 | Baixa o DANFE |

## 6. Telas

- **Produtos → Dados → Fiscal**: NCM, CEST, CFOP, CSOSN/CST, origem, unidade.
- **Produtos**: badge "Sem NCM" e filtro **"Pendências fiscais"**.
- **Config → Fiscal**: provedor, ambiente, regime, IE, impressão, reenvio,
  série/último número, status do token e botão **"Testar conexão"**.
- **PDV → modal de pagamento**: **Finalizar** e **Emitir nota**.
- **Vendas**: badge por venda (`Sem nota`, `Pendente`, `Autorizada`, `Cancelada`),
  ações (emitir, reenviar, cancelar nota, XML/DANFE) e banner de pendências.

## 7. Checklist de homologação (Fase 2)

- [ ] Token de homologação no `.env`
- [ ] Certificado A1 e-CNPJ cadastrado no painel do Brasil NFe
- [ ] Emitente completo (CNPJ, IE, endereço, CRT)
- [ ] Produtos de teste com NCM/CFOP/CSOSN
- [ ] Emitir venda simples (1 item, dinheiro)
- [ ] Emitir com desconto
- [ ] Emitir com pagamento dividido
- [ ] Emitir com CPF e sem CPF
- [ ] Emitir fiado (`tPag 99`)
- [ ] Cancelar dentro do prazo (com justificativa)
- [ ] Reenviar nota pendente (simular queda)
- [ ] Reimprimir cupom/DANFE
- [ ] Conferir XML e QR Code
- [ ] Migrar numeração (série/último número)
- [ ] Trocar `fiscal.environment` para `producao` e emitir 1 venda real

## 8. Fora de escopo (por enquanto)

- NF-e modelo 55 (vendas para empresa/interestadual)
- NFS-e
- Carta de correção
- Devolução fiscal
- SPED / SINTEGRA
- Emissão de vendas avulsas
- Agente local de contingência offline
