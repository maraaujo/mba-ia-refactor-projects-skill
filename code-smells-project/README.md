# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`.

## Arquitetura

Estrutura em camadas (MVC + Service):

- `app.py` — entry point / composition root (application factory)
- `config.py` — configuração via variáveis de ambiente
- `routes.py` — registro de rotas (Views/endpoints)
- `controllers/` — controllers HTTP finos (request/response)
- `services/` — regras de negócio e validação
- `models/` — acesso a dados (queries parametrizadas)
- `database.py` / `schema.py` — conexão e schema do banco
- `errors.py` — exceções de domínio e tratamento de erro centralizado
- `middleware.py` — autenticação administrativa

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env   # ajuste SECRET_KEY e ADMIN_TOKEN
python app.py
```

A aplicação sobe em `http://localhost:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo (senhas armazenadas com hash).

## Endpoint administrativo

`POST /admin/reset-db` apaga todos os dados e requer o header `X-Admin-Token` com o valor configurado em `ADMIN_TOKEN`. Sem essa variável configurada, o endpoint fica bloqueado.
