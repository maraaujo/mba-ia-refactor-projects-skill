# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
npm install
cp .env.example .env
npm start
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória e já carrega seeds automaticamente no boot.

## Variáveis de ambiente

Veja `.env.example`. Nenhuma credencial fica hardcoded no código — configure `PAYMENT_GATEWAY_KEY` e `ADMIN_API_KEY` antes de rodar em qualquer ambiente compartilhado.

## Autenticação administrativa

As rotas `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem o header `x-admin-key` com o valor configurado em `ADMIN_API_KEY`.

## Arquitetura

O código segue uma estrutura MVC em `src/`:

- `config/` — configuração via variáveis de ambiente
- `database/` — conexão, schema e seed do SQLite
- `models/` — acesso a dados (queries parametrizadas)
- `services/` — regra de negócio (checkout, relatório, exclusão de usuário, senha, gateway de pagamento)
- `controllers/` — tradução HTTP request/response, delegando para os services
- `routes/` — definição dos endpoints
- `middleware/` — autenticação administrativa e tratamento centralizado de erros
- `app.js` — composition root

Exemplos de requisições estão em `api.http`.
