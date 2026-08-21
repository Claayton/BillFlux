# 💸 BillFlux

[![MIT License](https://img.shields.io/badge/license-MIT-007EC7.svg?style=flat-square)](/LICENSE) [![Code Style Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black/)

Gerenciador de contas a pagar e vendas para pequeno comércio: boletos, produtos com estoque,
plano de contas, formas de pagamento e um PDV completo com recibo imprimível.

## 🏗️ Arquitetura

Separação total entre backend e frontend:

```
┌─────────────┐        ┌──────────────┐        ┌──────────────┐
│   Vue 3 SPA  │  HTTP  │   nginx      │  HTTP  │  Flask (API) │
│  (Vite dev)  │ ─────► │ (Vite proxy  │ ─────► │  JSON only   │
│              │  /api  │  / nginx)    │  /api  │              │
└─────────────┘        └──────────────┘        └──────┬───────┘
                                                       │
                                                  SQLite/SQLAlchemy
```

- **Flask** entrega **apenas JSON** em `/api/*` (auth, vendas, contas, produtos, plano de contas, formas de pagamento, PDV, recibo). Não renderiza HTML e não serve estáticos.
- **Vue 3** é responsável por todo o client: telas, componentes, máscaras, gráficos, código de barras e QR PIX.
- Em **desenvolvimento** o Vue roda no Vite (com proxy de `/api` para o Flask). Em **produção** um container nginx serve o build do SPA e faz o proxy.

## ✨ Features

- Autenticação com sessão + proteção CSRF (sem JWT)
- Contas a pagar: cadastro, edição, pagamento (com QR PIX e código de barras), detalhes, filtros
- Vendas: lançamento avulso por dia e vendas do PDV, com relatórios
- Produtos: catálogo, preço/custo, controle de estoque e movimentações
- Plano de contas (receitas/despesas com subcategorias) e formas de pagamento
- Visão geral: faturamento, ticket, lucro bruto, série diária (ECharts)
- PDV full-screen: busca por nome/código de barras, multiplicador `N*`, atalho `F2` e recibo imprimível

## 🧱 Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.10, Flask, SQLAlchemy/SQLModel, SQLite |
| Frontend | Vue 3, Vite, Element Plus, ECharts, Pinia, Vue Router |
| Infra | Docker Compose (api + nginx), Cloudflared (túnel) |
| Qualidade | pytest (backend), Vitest + Vue Test Utils (frontend), Black/Flake8 |

## 📁 Estrutura

```
billflux/
  api/                  # endpoints JSON (/api/*)
  infra/
    entities/           # modelos SQLModel
    repository/         # acesso a dados
  services/barcode.py   # utilidades de código de barras
frontend/
  src/
    api/client.js       # cliente HTTP com CSRF
    stores/             # Pinia (auth)
    utils/format.js     # máscara de moeda/data BR
    views/              # telas do SPA
    __tests__/          # testes Vitest
nginx/default.conf      # config do nginx de produção
Dockerfile              # imagem da API (JSON only)
Dockerfile.web          # imagem nginx com o build do SPA
```

## 🚀 Desenvolvimento

Requisitos: Python 3.10+ e Node 18+.

### Backend (API)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt          # inclui ferramentas de dev/teste
flask --app run run --debug              # API em http://localhost:5000
```

> Dica: para usar um banco separado do de produção, defina `BILLFLUX_DATABASE__URL=sqlite:///billflux_dev.db`.

### Frontend (SPA)

```bash
cd frontend
npm install
npm run dev                               # Vite em http://localhost:5174
```

O Vite já tem proxy de `/api` para `http://localhost:5000`. Para apontar para outra porta:

```bash
BILLFLUX_API_TARGET=http://localhost:5001 npm run dev
```

Abra `http://localhost:5174` — todas as rotas (Vendas, Contas, Produtos, PDV etc.) são do Vue Router.

### 🔐 Credenciais de desenvolvimento

```
Usuário: admin
Senha:   admin
```

Definidas em `settings.toml` (seção `[auth]`, senha em hash). Para trocar:

```bash
python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('sua-senha'))"
```

## 🧪 Testes

```bash
# Backend (pytest)
BILLFLUX_DATABASE__URL=sqlite:// python3 -m pytest

# Frontend (Vitest)
cd frontend && npm test          # executa uma vez
cd frontend && npm run test:watch
```

## 🐳 Produção (Docker)

```bash
docker compose up -d --build
```

Sobe dois serviços:

- `api` — Flask (JSON only), exposto apenas internamente na porta 5000
- `web` — nginx na porta **80**: serve o build do SPA e faz proxy de `/api` para o `api`

O banco é um volume (`billflux-data`) montado em `/app/data`.

### Variáveis de ambiente

| Variável | Descrição | Padrão |
|---|---|---|
| `BILLFLUX_DATABASE__URL` | Caminho do SQLite | `sqlite:///data/billflux.db` |
| `BILLFLUX_SECRET_KEY` | Chave de sessão/CSRF (**obrigatória em produção**) | `change-me` |
| `BILLFLUX_AUTH__ALLOW_SIGNUP` | Permite criar conta | `false` |
| `BILLFLUX_AUTH__USERNAME` | Usuário padrão criado no boot | `coqueiral` |
| `BILLFLUX_AUTH__PASSWORD_HASH` | Hash scrypt da senha do usuário padrão | — |

> A imagem de produção instala apenas `requirements-prod.txt` (runtime). `requirements.txt` é usado no desenvolvimento/testes.

## 📝 Notas

- Valores monetários trafegam como **número** (float) na API — sem ambiguidade de formato.
- As datas em formato `YYYY-MM-DD` são tratadas como **data local** no frontend para evitar deslocamento de fuso.
- Formas de pagamento e categorias já usadas em registros não podem ser excluídas — apenas desativadas/renomeadas.
