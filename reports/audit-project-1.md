# Architectural Audit Report — code-smells-project

> Gerado pela skill `refactor-arch`. Fase 2 (auditoria) seguida de Fase 3 (refatoração), com um ajuste posterior solicitado pelo usuário em relação ao endpoint `/admin/query`.

## Project Analysis (Fase 1)

- **Language:** Python 3
- **Framework:** Flask 3.1.1 (+ flask-cors 5.0.1)
- **Database:** SQLite (`loja.db`)
- **ORM / Database Library:** Nenhum ORM — driver nativo `sqlite3`
- **Application Type:** API REST monolítica (e-commerce: produtos, usuários, pedidos, relatórios)
- **Entry Point (pós-refatoração):** `app.py` (application factory `create_app()`)
- **Current Architecture (pós-refatoração):** MVC + Service layer — `controllers/`, `services/`, `models/`, `routes.py`, `database.py`/`schema.py`, `errors.py`, `middleware.py`

## Summary

| Severity | Count | Status |
|---|---|---|
| CRITICAL | 5 | Todos corrigidos |
| HIGH | 5 | Todos corrigidos |
| MEDIUM | 7 | Todos corrigidos |
| LOW | 5 | Todos corrigidos |

---

## CRITICAL

### C1 — SQL Injection via concatenação de strings
- **Arquivo original:** `models.py` (múltiplas funções)
- **Descrição:** SQL construído por concatenação direta de valores do usuário.
- **Impacto:** Manipulação de queries, bypass de autenticação, exfiltração/corrupção de dados.
- **Status:** ✅ **Corrigido** — todas as queries em `models/*.py` usam parâmetros (`?`) via `sqlite3`.

### C2 — Execução arbitrária de SQL vindo do cliente (`/admin/query`)
- **Arquivo original:** `app.py:71-94`
- **Descrição:** O endpoint recebia `sql` no corpo da requisição e executava via `cursor.execute(query)`, sem restrição.
- **Impacto:** Controle total sobre o banco de dados.
- **Status:** ⚠️ **Neutralizado (não removido)** — atualizado a pedido do usuário em 2026-09-05.
  A rota `POST /admin/query` foi **preservada** para manter compatibilidade de contrato com os endpoints originais, mas foi transformada em um endpoint inerte:
  - Não lê nem processa o corpo da requisição.
  - Não contém nenhuma chamada `cursor.execute()` ou execução de SQL de qualquer forma.
  - Retorna sempre `HTTP 410 Gone` com um JSON informando que a funcionalidade foi desabilitada por segurança.
  - Implementação: `controllers/admin_controller.py::executar_query_desabilitado`, registrada em `routes.py`.
  - Validado via curl com payload malicioso (`{"sql": "DROP TABLE produtos"}`) — endpoint retornou 410 e a tabela `produtos` permaneceu intacta.

### C3 — Endpoint destrutivo sem autenticação/autorização (`/admin/reset-db`)
- **Arquivo original:** `app.py:57-69`
- **Status:** ✅ **Corrigido** — protegido por `middleware.admin_required`, exigindo header `X-Admin-Token` igual ao configurado em `ADMIN_TOKEN` (variável de ambiente). Sem essa variável configurada, o endpoint fica bloqueado por padrão.

### C4 — Segredos e senha expostos em resposta de API (`/health`)
- **Arquivo original:** `controllers.py:294-295`, `app.py:11`
- **Status:** ✅ **Corrigido** — `SECRET_KEY` movida para variável de ambiente (`config.py`); `/health` não retorna mais `secret_key`, `debug`, `ambiente` ou `db_path`.

### C5 — Senhas em texto plano armazenadas e expostas
- **Arquivo original:** `database.py`, `models.py` (get_todos_usuarios, get_usuario_por_id, login_usuario)
- **Status:** ✅ **Corrigido** — senhas hasheadas com `werkzeug.security.generate_password_hash`/`check_password_hash`; campo `senha` nunca é incluído nas respostas públicas da API (`models/usuario_model.py::_row_para_dict_publico`).

---

## HIGH

### H1 — Debug mode habilitado
- **Status:** ✅ **Corrigido** — `DEBUG` controlado por `FLASK_DEBUG` (env var), padrão `false`.

### H2 — Acesso direto ao banco na camada de aplicação/roteamento
- **Status:** ✅ **Corrigido** — rotas administrativas movidas para `controllers/admin_controller.py`, seguindo a mesma camada das demais rotas.

### H3 — Lógica de negócio dentro dos Controllers
- **Status:** ✅ **Corrigido** — validação de domínio extraída para `services/produto_service.py`.

### H4 — Lógica de negócio dentro do Model
- **Status:** ✅ **Corrigido** — cálculo de total/estoque movido para `services/pedido_service.py`; regras de desconto movidas para `services/relatorio_service.py`.

### H5 — Estado global mutável (conexão de banco em variável de módulo)
- **Status:** ✅ **Corrigido** — conexão por contexto de requisição via `flask.g` (`database.py`), sem variável global de módulo.

---

## MEDIUM

### M1 — N+1 Queries
- **Status:** ✅ **Corrigido** — `models/pedido_model.py` usa uma única query com `LEFT JOIN` (pedidos + itens + produtos), agrupada em Python.

### M2 — Duplicação entre `get_pedidos_usuario` e `get_todos_pedidos`
- **Status:** ✅ **Corrigido** — ambas reutilizam a mesma query base parametrizada por filtro opcional.

### M3 — Duplicação de validação entre criar/atualizar produto
- **Status:** ✅ **Corrigido** — validação centralizada em `services/produto_service.py::_validar_dados_produto`.

### M4 — Ausência de integridade referencial no schema
- **Status:** ✅ **Corrigido** — `FOREIGN KEY` adicionadas em `pedidos.usuario_id`, `itens_pedido.pedido_id` e `itens_pedido.produto_id`; `PRAGMA foreign_keys = ON` habilitado por conexão.

### M5 — Tratamento de erro repetitivo e vazamento de detalhes de exceção
- **Status:** ✅ **Corrigido** — tratamento centralizado em `errors.py` (`AppError` + `@app.errorhandler`); controllers não têm mais `try/except` repetido.

### M6 — CORS aberto globalmente
- **Status:** ✅ **Corrigido (configurável)** — origem controlada por `CORS_ORIGINS` (env var); padrão mantém comportamento original (`*`) para não quebrar o contrato, mas agora é configurável por ambiente.

### M7 — Magic strings de status de pedido repetidas
- **Status:** ✅ **Corrigido** — centralizado em `constants.py` (`STATUS_PEDIDO_VALIDOS`, etc.).

---

## LOW

### L1 — Import não utilizado (`os` em `database.py`)
- **Status:** ✅ **Corrigido** — código reescrito, sem imports não usados.

### L2 — Caminho do banco hardcoded
- **Status:** ✅ **Corrigido** — `DATABASE_PATH` via variável de ambiente (`config.py`).

### L3 — Magic numbers de validação de nome
- **Status:** ✅ **Corrigido** — `NOME_PRODUTO_TAMANHO_MINIMO`/`MAXIMO` em `constants.py`.

### L4 — Uso de `print()` para logging
- **Status:** ✅ **Corrigido** — substituído por `logging` padrão do Python, configurado em `app.py`.

### L5 — Categorias válidas hardcoded no controller
- **Status:** ✅ **Corrigido** — `CATEGORIAS_VALIDAS` centralizado em `constants.py`.

---

## Changelog

- **2026-09-05** — Fase 3 concluída: reestruturação completa para MVC + Service layer; todos os findings CRITICAL/HIGH/MEDIUM/LOW corrigidos; validação funcional via execução real do servidor e testes com `curl`.
- **2026-09-05 (ajuste posterior)** — A pedido do usuário, `POST /admin/query` foi restaurado como rota (requisito: todos os endpoints originais devem continuar respondendo), porém mantido **neutralizado**: não lê o corpo da requisição, não executa SQL, e responde sempre `410 Gone`. Finding C2 atualizado de "endpoint removido" para "endpoint neutralizado, rota preservada". Validado com payload malicioso (`DROP TABLE`) confirmando que nenhuma operação é executada. Todos os 19 endpoints originais foram testados individualmente e continuam respondendo.
