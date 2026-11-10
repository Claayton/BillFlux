# Brasil NFe — contrato usado pelo BeeFlux

> Referência: <https://www.brasilnfe.com.br/api> e <https://www.brasilnfe.com.br/docs>.
> Adapter: `billflux/services/fiscal/brasilnfe.py`.

## 1. Conexão e autenticação

| Item | Valor |
|---|---|
| Base | `https://api.brasilnfe.com.br/services` |
| Header | `Token: <token da empresa>` |
| Content-Type | `application/json` |
| Timeout padrão | 60 s |
| Transporte | `urllib.request` (sem dependência extra), injetável nos testes |

O token é lido de `BRASILNFE_TOKEN` (`.env`). Ele **não** é gravado no banco.
`UserToken` não é usado: só seria necessário para a seção `Empresas`
(numeração/certificado).

## 2. Endpoints usados

| Operação | Método | Caminho |
|---|---|---|
| Emitir | `POST` | `/fiscal/EnviarNotaFiscal` |
| Cancelar | `POST` | `/fiscal/CancelarNotaFiscal` |
| Consultar | `POST` | `/fiscal/ConsultarNotaFiscal` |
| XML/DANFE | `POST` | `/fiscal/ObterArquivoNotaFiscal` |
| Status SEFAZ | `POST` | `/fiscal/ConsultarStatusSefaz` |

## 3. Emissão

### Regras gerais

- `ModeloDocumento` é **sempre 65** (NFC-e). O default do provedor é 55.
- `TipoAmbiente`: `2` homologação, `1` produção.
- `Serie`, `Numero` e `Lote` são **omitidos** → o provedor controla a
  numeração (série + ambiente).
- `IdentificadorInterno = "VENDA-<order_id>"` → idempotência e consulta.
- `DataEmissao` = data/hora do momento da emissão no fuso `-03:00`.
- `Finalidade=1`, `IndicadorPresenca=1`, `TipoDanfe=4`,
  `ConsumidorFinal=true`, `CalcularIBPT=true`.
- `NaturezaOperacao = "Venda de mercadoria"`.
- `ValorTotal` = total da venda (já líquido de desconto).
- `ValorDesconto` = desconto da venda (o provedor distribui nos itens).

### Produtos

| Nosso campo | Provedor |
|---|---|
| `Product.id` | `CodProdutoServico` |
| `Product.name` | `NmProduto` |
| `Product.ncm` (8 dígitos) | `NCM` |
| `Product.cest` (7 dígitos) | `CEST` (quando houver) |
| `Product.barcode` válido | `EAN` |
| sem GTIN válido | `"SEM GTIN"` |
| `Product.cfop` ou `5102` | `CFOP` |
| `Product.fiscal_unit` ou `UN` | `UnidadeComercial` |
| `Product.origem` | `OrigemProduto` |
| `Product.csosn` ou `102` (CRT 1/4) | `Imposto.ICMS.CodSituacaoTributaria` |
| `Product.cst` ou `00` (CRT 2/3) | `Imposto.ICMS.CodSituacaoTributaria` |
| Simples/MEI (com `csosn`) | `Imposto.PIS`/`COFINS` com CST `49` (recolhidos no DAS) |
| Regime Normal (com `cst`) | `Imposto.PIS`/`COFINS` com CST `01` (0,65% / 3,00%) |
| quantidade vendida | `Quantidade` |
| preço da apresentação | `ValorUnitario` |
| quantidade × preço | `ValorTotal` |

**Somente o NCM bloqueia a emissão.** CFOP, CSOSN/CST, origem e unidade têm
padrões. GTIN inválido vira `SEM GTIN` em vez de rejeição 611/612.

### Cliente

- Só vai no payload quando o CPF/CNPJ tem 11 ou 14 dígitos (somente números).
- Sem cliente identificado → bloco `Cliente` omitido (consumidor não
  identificado).
- `IndicadorIe = 9` (não contribuinte).
- `Contato` com telefone/e-mail quando cadastrados.

### Pagamentos

| Forma no BeeFlux | `FormaPagamento` | `IndicadorPagamento` |
|---|---|---|
| Dinheiro | `01` | `0` |
| Cheque | `02` | `0` |
| Crédito | `03` | `0` |
| Débito | `04` | `0` |
| Cartão da loja | `05` | `0` |
| Vale alimentação | `10` | `0` |
| VR/VA | `11` | `0` |
| Boleto | `15` | `0` |
| Depósito | `16` | `0` |
| PIX dinâmico | `17` | `0` |
| Transferência/TED/DOC | `18` | `0` |
| PIX | `20` | `0` |
| Fiado/crediário | `99` + `Descricao` | `1` |
| Outros | `99` + `Descricao` | `0` |

Pagamento dividido → uma linha por forma. `VlPago` é o valor da venda
(não há troco no fluxo atual).

## 4. Resposta de emissão

```json
{
  "Base64Xml": "...",
  "Base64File": "...",
  "ReturnNF": {
    "Ok": true,
    "ChaveNF": "44 dígitos",
    "NumeroProtocolo": "135...",
    "Serie": 1,
    "Numero": 42,
    "CodStatusRespostaSefaz": 100,
    "DsStatusRespostaSefaz": "Autorizado o uso da NF-e"
  },
  "Error": "",
  "Avisos": []
}
```

A rejeição **vem com HTTP 200**; o resultado real está em `ReturnNF.Ok`.
O adapter nunca confia no status HTTP.

### Mapeamento de status

| Situação | Status interno |
|---|---|
| `Ok=true` com chave e protocolo | `autorizada` |
| `Ok=true` sem chave/protocolo | `pendente_autorizacao` |
| `CodStatusRespostaSefaz` em `103/105/108/109` | `pendente_autorizacao` |
| `CodStatusRespostaSefaz` em `110/301/302` | `denegada` |
| demais falhas | `rejeitada` |

`pendente_autorizacao` existe para a **contingência automática da NFC-e**
(`tpEmis=9`): a nota já vale, mas o protocolo ainda não chegou. O banner não
deve tratar esse estado como erro.

## 5. Consulta (idempotência)

Payload:

```json
{"IdentificadorInterno": "VENDA-123", "RetornarArquivos": true}
```

ou, quando já há chave:

```json
{"Chave": "<44 dígitos>", "RetornarArquivos": true}
```

`Nota.Status`: `1` autorizada, `2` cancelada, `3` rejeitada, `4` denegada,
`5` em processamento.

Antes de reenviar uma nota com tentativa anterior, o serviço consulta pelo
identificador. Se já estiver autorizada, apenas grava o retorno — **não emite
de novo**. Rejeitada/denegada não é documento válido, então pode ser reemitida.

## 6. Cancelamento

```json
{"ChaveNF": "<44 dígitos>", "Justificativa": "15 a 1000 caracteres"}
```

Sucesso quando `Status=1` e `CodStatusRespostaSefaz` em `135/155` (ou ausente).
Falha (`Status=3`, `Error` preenchido etc.) vira
`FiscalCancellationError`; a venda **não** é cancelada.

Prazo da NFC-e: **30 minutos**. Fora do prazo a SEFAZ recusa e o BeeFlux
bloqueia o cancelamento da venda, orientando o usuário.

## 7. XML e DANFE

```json
{"ChaveNF": "<44 dígitos>", "FileType": 1, "TipoDocumentoFiscal": 1}
```

- `FileType=1` → XML; `FileType=2` → PDF/DANFE.
- A resposta é uma **string Base64 pura** (JSON string), não um objeto.
- O BeeFlux guarda o XML/DANFE no `fiscal_document` após o primeiro download.
- O DANFE da NFC-e pode vir em **PDF ou HTML**; a API do BeeFlux detecta pelo
  conteúdo e responde com o `Content-Type` correto.

## 8. Testar conexão

```json
{"ModeloDocumento": 65}
```

Resposta: `status=0` (consulta processada),
`CodStatusRespostaSefaz=107` (serviço em operação),
`DsStatusRespostaSefaz` com a descrição.

## 9. Erros e limites

- HTTP ≥ 400, timeout, DNS, resposta não-JSON → `FiscalTransportError`.
- Token ausente/CNPJ/IE ausentes → `FiscalConfigError`; a nota fica
  **pendente** com a mensagem, para reenviar depois de corrigir a configuração.
- NCM ausente → `FiscalValidationError`; a nota fica **pendente** e o provedor
  não é chamado.
- Numeração automática: não usamos `ConsultarNumeracao`/`AtualizarNumeracao`
  nesta fase (exigiriam `UserToken`). Para migrar uma série existente, os
  campos `fiscal.nfce_series`/`fiscal.nfce_last_number` já estão no cadastro,
  mas o envio manual fica para quando houver necessidade.
