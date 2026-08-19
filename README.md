# 💸 BillFlux
[![MIT License](https://img.shields.io/badge/license-MIT-007EC7.svg?style=flat-square)](/LICENSE) ![GitHub issues](https://img.shields.io/github/issues/Claayton/BillFlux.svg) ![GitHub stars](https://img.shields.io/github/stars/Claayton/BillFlux.svg) ![GitHub last commit](https://img.shields.io/github/last-commit/Claayton/BillFlux.svg) [![Code Style Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black/)

## 📋 Features

- Sistema para gerenciamento e administração de boletos e contas a pagar, com o objetivo de ser simples, direto e usual. As principais funcionalidades incluem:
  - Desenvolvido em Python/Flask
  - Cadastro e listagem de contas a pagar (boletos)
  - Filtros por status (pagas, vencidas, à vencer, hoje)

### 🗺️ Roadmap

- CRUD de usuários e autenticação
- Geração de código de barras para facilitar o pagamento, evitando a necessidade de digitar o código manualmente no smartphone ou de utilizar o boleto em papel

## 🚀 Quick Start

O projeto foi desenvolvido em um sistema operacional `Linux Mint 22`, utilizando a versão `3.10.2` do Python. As instruções devem funcionar em qualquer sistema baseado no Ubuntu e com qualquer versão do Python acima da 3.8, mas é recomendado utilizar um ambiente o mais semelhante possível para evitar conflitos.

Eu utilizei `pyenv` para instalar o Python, mas você pode utilizar o [site oficial](https://www.python.org/downloads/) se preferir.

### Ambiente Virtual

É uma boa prática criar um ambiente virtual para isolar o projeto da sua máquina e evitar conflitos. Para instalar o `virtualenv`, caso ainda não tenha, utilize:

```bash
sudo pip3 install virtualenv
```
Agora configure seu `ambiente virtual` para evitar possiveis conflitos:
```
python3 -m venv venv 
```
*Em seguida você deverá `ativar` esse ambiente:*
```
source venv/bin/activate 
```
*Agora instale as `bibliotecas e pacotes` necessários para rodar o projeto:*
```
pip3 install -r requirements.txt
```

*🎉 O projeto já está configurado e pronto para ser testado em modo de desenvolvedor:*
```
flask --app run run --debug
```

## 🔐 Login (modo desenvolvimento)

Para acessar a área de contas, use o usuário padrão:

```
Usuário: admin
Senha:   admin
```

As credenciais ficam em `settings.toml` (seção `[auth]`, senha em hash). Para trocar em produção,
utilize as variáveis de ambiente `BILLFLUX_AUTH__USERNAME` e `BILLFLUX_AUTH__PASSWORD_HASH`.

Para gerar um novo hash de senha:

```python
python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('sua-senha'))"
```

> Em produção, defina também `BILLFLUX_SECRET_KEY` (usado nas sessões e no CSRF). O valor padrão
> `change-me` é apenas para desenvolvimento.

## 🐳 Docker

```
docker compose up --build
```

A aplicação fica disponível em `http://localhost:5000`.

## ⚙️ Tests

Utilizar para esse projeto o pytest para fazer os testes necessários, para executar os testes utilize:

```
  # Rodar os testes + cobertura, mostrando os detalhes caso ocorra algum erro:
  pytest -v

```
