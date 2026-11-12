# Agente de impressão (Windows)

App pequeno que fica na **bandeja do Windows** e imprime os cupons/DANFE do
BillFlux **direto na impressora**, sem o diálogo do navegador e sem o
cabeçalho/rodapé (data, URL do site) que o Chrome/Edge adicionam.

Ele não é um navegador empacotado nem um instalador gigante: é um `.exe`
.NET Framework 4.8 + WebView2 (que já vem no Windows 10/11).

## O que resolve

| Problema | Como o agente resolve |
| --- | --- |
| Diálogo de impressão a cada venda | Impressão silenciosa via `CoreWebView2.PrintAsync` |
| Cabeçalho com data e “BeeFlux” | `ShouldPrintHeaderAndFooter = false` |
| Rodapé com o endereço do site | idem (o navegador não injeta nada) |
| Papel 58/80 mm errado | Página configurada em mm pelo tamanho medido no app |
| Escolher impressora por venda | Impressora configurada na bandeja (ou a padrão do Windows) |

## Como funciona

```text
BillFlux (navegador)                Agente (bandeja)
      |                                   |
      |  POST http://127.0.0.1:9911/print |
      |  { bodyHtml, css, widthMm, ... }  |
      |---------------------------------->|  WebView2 invisível renderiza o HTML
      |                                   |  PrintAsync(impressora, 80mm, margem 0)
      |<----------------------------------|  { ok: true }
```

- O agente escuta **somente em `127.0.0.1`** (nada exposto na rede).
- O frontend tenta o agente primeiro; se ele não estiver aberto, cai no
  `window.print()` de hoje. Nada quebra para quem usa só o navegador.
- O HTML sai do próprio BillFlux: o DANFE em HTML vai como veio do provedor,
  o cupom/comanda vai como clone do preview com o CSS da aplicação.

### Endpoints

| Método | Rota | Descrição |
| --- | --- | --- |
| `GET` | `/status` | Versão, impressora, papel, `busy` e impressoras instaladas |
| `GET` | `/printers` | Impressoras instaladas no Windows |
| `GET` | `/config` | Configuração atual |
| `POST` | `/config` | Altera `printer` e/ou `widthMm` (58/80) |
| `POST` | `/print` | Imprime `{ bodyHtml, css, widthMm, heightMm, printer }` |

Exemplo manual (PowerShell):

```powershell
Invoke-RestMethod http://127.0.0.1:9911/status

Invoke-RestMethod http://127.0.0.1:9911/print -Method Post -ContentType 'application/json' -Body (@{
  bodyHtml = '<div style="font-family:Arial">Teste BillFlux</div>'
  widthMm  = 80
  heightMm = 60
} | ConvertTo-Json)
```

## Instalação no caixa

1. Baixe o artefato **`BillFlux-PrintAgent-win-x64.zip`** na aba *Actions* do
   GitHub (workflow **Print agent**) ou na Release, quando houver.
2. Extraia para uma pasta fixa, por exemplo `C:\BillFlux\PrintAgent\`.
   - Não precisa instalar nada.
   - A pasta precisa ficar no mesmo lugar: o “iniciar com o Windows” aponta
     para o caminho do `.exe`.
3. Execute `BillFlux.PrintAgent.exe`.
   - O SmartScreen pode avisar na primeira vez (sem assinatura digital):
     **Mais informações → Executar assim mesmo**.
   - Aparece um ícone de impressora na bandeja.
4. Clique no ícone → **Impressora** → escolha a térmica.
5. Em **Papel**, escolha **58 mm** ou **80 mm** (o mesmo configurado no
   BillFlux em Configurações → Cupom).
6. Marque **Iniciar com o Windows** para o agente subir sozinho.
7. Use **Imprimir teste** para conferir: deve sair sem cabeçalho/rodapé e no
   tamanho do papel.

> Dica: se a impressora do caixa é a única, pode deixar **Impressora padrão do
> Windows**. Se houver mais de uma, escolha a térmica no agente.

### Atualizar

Feche o agente (bandeja → **Sair**), substitua os arquivos da pasta e abra de
novo. A configuração fica em `%APPDATA%\BillFlux\print-agent.json` e não é
perdida.

## Onde ficam os arquivos

| Item | Caminho |
| --- | --- |
| Configuração | `%APPDATA%\BillFlux\print-agent.json` |
| Log | `%APPDATA%\BillFlux\print-agent.log` |
| Cache do WebView2 | `%LOCALAPPDATA%\BillFlux\WebView2` |
| HTML temporário | `%TEMP%\BillFluxPrint` |

A bandeja tem **Abrir pasta de configuração** para chegar rápido nesses
arquivos.

## No BillFlux

- `frontend/src/utils/printBridge.js` concentra a ponte (`getAgentStatus`,
  `agentPrint`, `printElementWithAgent`).
- `frontend/src/utils/danfe.js` usa o agente para DANFE em HTML e em PDF
  (rasterizado).
- `SaleReceiptModal.vue` (cupom pós-venda/reimpressão) e `TabPrintModal.vue`
  (comanda) tentam o agente antes do `window.print()`.
- O endereço padrão é `http://127.0.0.1:9911`. Para usar outra porta, defina
  `VITE_PRINT_AGENT_URL` no build do frontend.

### Segurança

- O servidor só abre socket em `127.0.0.1` (ninguém da rede acessa).
- CORS libera apenas leitura/impressão; o agente não expõe arquivos nem
  comandos.
- `OPTIONS` responde ao preflight, inclusive
  `Access-Control-Allow-Private-Network` (exigido pelo Chrome quando o
  BillFlux está num domínio público chamando o localhost).
- O agente não usa administrador: nada de URL ACL do `HttpListener`.

## Desenvolvimento

Projeto: `desktop/print-agent/src/BillFlux.PrintAgent/`

```powershell
dotnet restore desktop/print-agent/src/BillFlux.PrintAgent/BillFlux.PrintAgent.csproj
dotnet build desktop/print-agent/src/BillFlux.PrintAgent/BillFlux.PrintAgent.csproj -c Release
dotnet run --project desktop/print-agent/src/BillFlux.PrintAgent/BillFlux.PrintAgent.csproj
```

O `.exe` sai em
`desktop/print-agent/src/BillFlux.PrintAgent/bin/Release/BillFlux.PrintAgent.exe`
com as DLLs do WebView2 ao lado.

No CI, `.github/workflows/print-agent.yml` compila no `windows-latest` e publica
o ZIP como artefato. Binários **não** entram no git.

Requisitos para compilar: .NET SDK 8 (para o `dotnet build`) e o runtime do
WebView2 na máquina que for imprimir. O runtime já acompanha o Windows 10/11;
se faltar, instale o **Microsoft Edge WebView2 Runtime**.

## Problemas comuns

| Sintoma | Causa provável | Solução |
| --- | --- | --- |
| BillFlux abre o diálogo do navegador | Agente fechado ou porta diferente | Abra o agente; confira o ícone na bandeja |
| “Não foi possível iniciar o serviço local” | Outra instância/porta 9911 ocupada | Feche o outro agente e reabra |
| “WebView2 indisponível” | Runtime ausente/corrompido | Instale o WebView2 Runtime |
| Sai na impressora errada | Impressora padrão do Windows ou escolha no agente | Escolha a térmica em **Impressora** |
| Cupom cortado/curto | Papel configurado diferente do driver | Alinhe 58/80 mm no agente e no BillFlux |
| SmartScreen bloqueia | `.exe` sem assinatura digital | **Mais informações → Executar assim mesmo** |
