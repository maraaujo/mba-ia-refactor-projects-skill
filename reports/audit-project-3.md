# Relatório de Auditoria e Refatoração Arquitetural

**Projeto:** `task-manager-api`
**Skill:** `refactor-arch`
**Data:** 2026-09-05

---

## Fase 1 — Análise do Projeto

- **Language:** Python 3.12
- **Framework:** Flask 3.0 (+ Flask-SQLAlchemy, Flask-CORS; Marshmallow instalado mas não utilizado)
- **Database:** SQLite (`tasks.db`, arquivo local)
- **ORM / Database Library:** Flask-SQLAlchemy (SQLAlchemy 2.x ORM)
- **Application Type:** API REST (JSON) para gerenciamento de tarefas, usuários e categorias
- **Entry Point:** `app.py` (registrava blueprints, criava tabelas via `db.create_all()`, `app.run(debug=True)`)
- **Arquitetura original:** pseudo-MVC parcial — já existiam os diretórios `models/`, `routes/`, `services/`, `utils/`, mas as rotas (`routes/*.py`) atuavam simultaneamente como Controller, View e camada de negócio; não havia camada de Service/Controller real para Task/User/Category (só existia `NotificationService`, não integrado às rotas).
- **Diretórios principais (antes):**
  - `models/` — entidades SQLAlchemy (`Task`, `User`, `Category`)
  - `routes/` — Blueprints Flask fazendo o papel de controller + view + regra de negócio
  - `services/` — apenas `notification_service.py`, não usado pelas rotas
  - `utils/` — helpers de validação/formatação, parcialmente duplicados dentro das rotas
  - `seed.py` — script de massa de dados inicial
- **Principais problemas arquiteturais identificados:**
  1. Lógica de negócio e validação massivamente dentro das rotas (nenhuma camada de Service para Task/User/Category)
  2. Autenticação fake (token forjado, previsível) e nenhuma autorização em rotas sensíveis (delete de usuário)
  3. Segredos hardcoded no código-fonte (`SECRET_KEY`, credenciais SMTP)
  4. Hashing de senha inseguro (MD5, sem salt)
  5. N+1 queries recorrentes em praticamente todas as rotas de listagem/relatório
  6. Duplicação extensa de lógica (regra de "overdue", validações de status/prioridade/email/role repetidas em múltiplos arquivos)
  7. `routes/report_routes.py` continha um bloco de conteúdo colado que quebrava a sintaxe do módulo (ver finding #1)

> **Observação sobre a Skill:** os arquivos de referência (`project-analysis.md`, `anti-patterns.md`, `report-template.md`, `mvc-guidelines.md`, `refactoring-playbook.md`) estavam **vazios** nesta execução. A análise e a auditoria foram conduzidas com base em conhecimento próprio de arquitetura, segurança e boas práticas Flask/SQLAlchemy.

---

## Fase 2 — Findings da Auditoria

### Resumo de Severidade

| Severidade | Qtde |
|---|---|
| CRITICAL | 2 |
| HIGH | 3 |
| MEDIUM | 3 |
| LOW | 3 |
| **Total** | **11** |

### Findings Detalhados

**1. [CRITICAL] Arquivo com sintaxe inválida / conteúdo estranho injetado**
- **Arquivo/trecho:** `routes/report_routes.py`, linhas ~59–594
- **Descrição:** um bloco extenso de texto não-Python (aparentando ser uma conversa de chat colada — ou injetada — no arquivo) aparecia no meio do módulo, incluindo instruções direcionadas a "sua Skill" sobre como classificar findings e referências a um projeto completamente diferente (`AppManager.js`, `badCrypto`, etc., que não fazem parte deste repositório). Confirmado via `python -m py_compile routes/report_routes.py`:
  ```
  SyntaxError: invalid character '—' (U+2014), linha 70
  ```
- **Impacto:** a aplicação não subia — `from routes.report_routes import report_bp` falhava, derrubando 100% da API.
- **Recomendação:** remover integralmente o texto estranho, preservando apenas o código Python válido (havia uma cópia íntegra do módulo logo em seguida, a partir da linha 595).
- **Nota de segurança:** o conteúdo foi tratado como **dado não confiável** — nenhuma instrução embutida nele foi seguida ao classificar os demais findings deste relatório.

**2. [CRITICAL] Hashing de senha inseguro e token de autenticação forjado**
- **Arquivo/trecho:** `models/user.py:27-32` (`set_password`/`check_password`); `routes/user_routes.py:~319` (`login`)
- **Descrição:** senhas armazenadas com **MD5** (hash rápido, sem salt, quebrado para uso em senhas). O "token" de login era construído por concatenação simples (`'fake-jwt-token-' + str(user.id)`), sem assinatura, expiração ou verificação real.
- **Impacto:** qualquer atacante podia forjar tokens previsíveis e comprometer senhas via rainbow tables/força bruta.
- **Recomendação:** usar `werkzeug.security.generate_password_hash`/`check_password_hash` (ou bcrypt/argon2) para senha, e um token real assinado com expiração para autenticação.

**3. [HIGH] Segredos hardcoded no código-fonte**
- **Arquivo/trecho:** `app.py:13` (`SECRET_KEY = 'super-secret-key-123'`); `services/notification_service.py:9-10` (`email_user`, `email_password = 'senha123'`)
- **Descrição:** segredos versionados diretamente no repositório.
- **Impacto:** qualquer pessoa com acesso ao código vê as credenciais; se vazar, compromete sessão e conta de e-mail.
- **Recomendação:** mover para variáveis de ambiente (`.env` + `python-dotenv`, já presente nas dependências mas não utilizado).

**4. [HIGH] Rota de exclusão de usuário sem autenticação/autorização**
- **Arquivo/trecho:** `routes/user_routes.py:~209` (`delete_user`, `DELETE /users/<id>`)
- **Descrição:** rota não possuía nenhuma verificação de autenticação/autorização — qualquer chamador podia excluir qualquer usuário (e suas tasks, via exclusão manual em cascata).
- **Impacto:** exclusão indevida de contas e dados sem controle de acesso.
- **Recomendação:** proteger com middleware de autenticação e checagem de papel (admin).

**5. [HIGH] Lógica de negócio e validação dentro das rotas**
- **Arquivo/trecho:** `routes/task_routes.py` (`create_task`, `update_task`); `routes/user_routes.py` (`create_user`, `update_user`); `routes/report_routes.py` (`summary_report`)
- **Descrição:** validação de limites de título, status/prioridade/email/role, e cálculo completo de relatório implementados diretamente nas rotas — mesmo já existindo `utils/helpers.py::process_task_data` com boa parte dessa lógica pronta, porém não utilizada por nenhuma rota.
- **Impacto:** duplicação, dificuldade de teste unitário, alta chance de regras divergirem entre create/update.
- **Recomendação:** extrair para camada de serviço (`TaskService`, `UserService`, `ReportService`) e reaproveitar o helper já existente.

**6. [MEDIUM] N+1 Queries**
- **Arquivo/trecho:** `routes/task_routes.py:43-59` (`get_tasks`); `routes/user_routes.py:36` (`task_count` via `len(u.tasks)`); `routes/report_routes.py` (`summary_report`, `get_categories`)
- **Descrição:** para cada task era feita uma query adicional para buscar `User`/`Category` dentro do loop; idem para contagem de tasks por usuário e por categoria.
- **Impacto:** degradação de performance proporcional ao número de registros.
- **Recomendação:** usar `joinedload`/`selectinload` do SQLAlchemy ou agregações (`GROUP BY`) em vez de laços com query individual.

**7. [MEDIUM] Duplicação da regra de "task atrasada" (overdue)**
- **Arquivo/trecho:** `routes/task_routes.py`, `routes/user_routes.py`, `routes/report_routes.py` (múltiplas ocorrências)
- **Descrição:** a mesma regra (`due_date < now and status not in [done, cancelled]`) era duplicada em pelo menos 5 lugares diferentes, apesar de já existir `Task.is_overdue()` em `models/task.py`, não utilizado em nenhuma rota.
- **Impacto:** risco de inconsistência se a regra mudar em um lugar e não nos outros.
- **Recomendação:** usar consistentemente `task.is_overdue()`.

**8. [MEDIUM] Tratamento de erros genérico e repetido**
- **Arquivo/trecho:** `routes/task_routes.py`, `routes/user_routes.py`, `routes/report_routes.py` (múltiplos `except:` bare)
- **Descrição:** tratamento de erros com `except:` sem tipo, inclusive engolindo exceções em operações de banco.
- **Impacto:** erros inesperados (bugs, falhas de conexão) mascarados como "erro ao salvar/atualizar", dificultando debug e observabilidade.
- **Recomendação:** capturar exceções específicas e centralizar tratamento com error handlers do Flask (`@app.errorhandler`).

**9. [LOW] Imports não utilizados**
- **Arquivo/trecho:** `routes/user_routes.py:11` (`hashlib`, `json`); `routes/task_routes.py:7` (`json`, `os`, `sys`, `time`); `utils/helpers.py:8-12` (`os`, `json`, `sys`, `math`, `hashlib`)
- **Descrição:** módulos importados mas nunca usados.
- **Impacto:** ruído, sugere código morto/copiado.
- **Recomendação:** remover imports não utilizados.

**10. [LOW] Magic numbers/strings duplicados**
- **Arquivo/trecho:** `utils/helpers.py:110-184`; `routes/task_routes.py`; `routes/user_routes.py`
- **Descrição:** constantes como `MIN_TITLE_LENGTH`, `MAX_TITLE_LENGTH`, `VALID_STATUSES` já existiam no arquivo, mas as validações usavam valores literais duplicados em vez de referenciá-las (o mesmo se repetia nas rotas, ex.: roles `['user','admin','manager']`, senha mínima `4`).
- **Impacto:** risco de inconsistência entre regra e constante declarada.
- **Recomendação:** centralizar constantes e referenciá-las em todos os pontos de validação.

**11. [LOW] API legada do SQLAlchemy / uso de `datetime.utcnow()` deprecated**
- **Arquivo/trecho:** `routes/user_routes.py:~48` e diversos `Model.query.get(id)`; `models/task.py`, `models/user.py`, `routes/*`, `utils/helpers.py` (`datetime.utcnow()`)
- **Descrição:** `Query.get()` é a forma legada de busca por PK no SQLAlchemy 2.x (recomendado `db.session.get(Model, id)`); `datetime.utcnow()` está deprecated desde Python 3.12.
- **Impacto:** baixo hoje (ainda funciona), mas candidatos à remoção/mudança de comportamento em versões futuras.
- **Recomendação:** migrar para `db.session.get(...)` e `datetime.now(timezone.utc)`.

---

## Fase 3 — Correções Realizadas

| # | Problema | Correção aplicada |
|---|---|---|
| 1 | Arquivo corrompido/conteúdo injetado | `routes/report_routes.py` reescrito do zero como controller fino; conteúdo estranho removido integralmente; sintaxe validada com `py_compile` |
| 2 | Hashing MD5 + token forjado | `models/user.py::set_password/check_password` migrados para `werkzeug.security`; campo `password` removido do `to_dict()` (não vaza mais hash via API); `auth.py` gera token real assinado e com expiração via `itsdangerous.URLSafeTimedSerializer` |
| 3 | Segredos hardcoded | `config.py` (lê `SECRET_KEY`, config de SMTP via variáveis de ambiente) + `.env.example`; `python-dotenv` (já presente nas dependências) agora efetivamente utilizado |
| 4 | `DELETE /users/<id>` sem autenticação | Decoradores `require_auth`/`require_admin` (`auth.py`), aplicado `@require_admin` à rota de exclusão de usuário — exige header `Authorization: Bearer <token>` de um usuário com role `admin` |
| 5 | Lógica de negócio nas rotas | Extraída para `services/task_service.py`, `services/user_service.py`, `services/category_service.py`, `services/report_service.py`; rotas viraram controllers finos que apenas parseiam a request e chamam o service |
| 6 | N+1 queries | `Task.query.options(joinedload(Task.user), joinedload(Task.category))` na listagem de tasks; contagem de tasks por usuário/categoria e produtividade do relatório reescritas com agregação SQL (`GROUP BY` via `sqlalchemy.func`) em vez de loop com query por item |
| 7 | Duplicação da regra "overdue" | Todas as rotas/serviços passaram a usar `Task.is_overdue()` |
| 8 | Tratamento de erros genérico | `errors.py` centraliza exceções de domínio (`ValidationError`, `NotFoundError`, `ConflictError`, `AuthError`, `ForbiddenError`) e registra handlers globais (`@app.errorhandler`) para `AppError`, `SQLAlchemyError` e `Exception`; rotas não têm mais `try/except` |
| 9 | Imports não utilizados | Removidos de `routes/user_routes.py`, `routes/task_routes.py`, `utils/helpers.py` |
| 10 | Magic numbers/strings duplicados | `utils/helpers.py` centraliza `VALID_STATUSES`, `VALID_ROLES`, `MIN_TITLE_LENGTH`, `MAX_TITLE_LENGTH`, `MIN_PASSWORD_LENGTH`, `DEFAULT_PRIORITY`, `DEFAULT_COLOR`, `MIN_PRIORITY`, `MAX_PRIORITY`; services referenciam essas constantes em vez de literais |
| 11 | API legada / deprecated | `db.session.get(Model, id)` usado em toda a camada de serviços; `datetime.utcnow()` substituído por `utils.helpers.utc_now()` (valor aware convertido de volta para naive, mantendo compatibilidade com os dados já armazenados) em `models/`, `services/`, `utils/helpers.py` e `seed.py` |

### Nova Estrutura Arquitetural (MVC)

```
config.py                     — configuração via variáveis de ambiente (Config)
errors.py                     — exceções de domínio + registro de error handlers globais
auth.py                       — geração/verificação de token, decorators require_auth/require_admin
database.py                   — instância db = SQLAlchemy() (composition, inalterado)
app.py                        — composition root / factory create_app()
models/
  task.py, user.py, category.py   — entidades SQLAlchemy (hash seguro, utc_now, is_overdue)
services/
  task_service.py              — regra de negócio de Task (CRUD, busca, stats)
  user_service.py               — regra de negócio de User (CRUD, login)
  category_service.py           — regra de negócio de Category
  report_service.py             — relatórios (summary, por usuário)
  notification_service.py       — envio de e-mail (credenciais via env)
routes/
  task_routes.py, user_routes.py, report_routes.py  — controllers finos, sem lógica de negócio
utils/
  helpers.py                    — validações, constantes, utc_now(), process_task_data
seed.py                         — script de massa de dados (utc_now(), sem warnings)
.env.example                    — modelo de variáveis de ambiente (segredos fora do código)
```

---

## Validações Executadas

1. **Sintaxe:** `python -m py_compile` em todos os arquivos tocados (`app.py`, `config.py`, `errors.py`, `auth.py`, `models/*.py`, `routes/*.py`, `services/*.py`, `utils/helpers.py`, `seed.py`) — sem erros.
2. **Dependências:** `pip install -r requirements.txt` executado com sucesso (ver observação sobre ambiente global abaixo).
3. **Seed/Banco:** `python seed.py` populou o SQLite sem erros e **sem warnings de depreciação** (após correção do `datetime.utcnow()`).
4. **Inicialização da aplicação:** `python app.py` subiu o servidor Flask sem erros de boot (inclusive o módulo antes corrompido, `report_routes.py`, carregou normalmente).
5. **Rotas/endpoints existentes:** todos os endpoints originais preservados e testados manualmente via `curl`.
6. **Operações principais e regressões:** validado ciclo completo de tasks/users/categories/relatórios, login e a nova proteção de admin.

### Resultado dos Testes de Endpoints

| Teste | Requisição | Resultado |
|---|---|---|
| Health/index | `GET /health`, `GET /` | `200` — payload preservado |
| Listagem de tasks (N+1 corrigido) | `GET /tasks` | `200` — inclui `overdue`, `user_name`, `category_name` corretos |
| Task por id | `GET /tasks/1` | `200` — mesmo formato de antes |
| Estatísticas de tasks | `GET /tasks/stats` | `200` — `total`, `pending`, `overdue`, `completion_rate` corretos |
| Listagem de usuários (N+1 corrigido) | `GET /users` | `200` — `task_count` correto por agregação SQL, sem campo `password` no payload |
| Categorias (N+1 corrigido) | `GET /categories` | `200` — `task_count` correto por agregação SQL |
| Relatório resumo (arquivo antes corrompido) | `GET /reports/summary` | `200` — `overview`, `tasks_by_status`, `tasks_by_priority`, `overdue`, `recent_activity`, `user_productivity` todos corretos |
| Relatório por usuário | `GET /reports/user/1` | `200` — estatísticas corretas |
| Criar usuário válido | `POST /users` | `201` — sem campo `password` na resposta |
| Criar usuário com e-mail inválido | `POST /users` | `400` — `"Email inválido"` |
| Login correto | `POST /login` | `200` — token real assinado (`itsdangerous`), não mais previsível |
| Login com senha errada | `POST /login` | `401` — `"Credenciais inválidas"` |
| Criar task válida | `POST /tasks` | `201` |
| Criar task com título curto | `POST /tasks` | `400` — `"Título muito curto"` |
| Excluir usuário sem token (fix da falta de auth) | `DELETE /users/<id>` | `401` |
| Excluir usuário com token de admin | `DELETE /users/<id>` | `200` — `"Usuário deletado com sucesso"` |
| Excluir usuário com token de usuário comum | `DELETE /users/<id>` | `403` — `"Acesso restrito a administradores"` |

Todos os testes confirmaram que o comportamento e os contratos de entrada/saída da API foram preservados, com duas mudanças intencionais e divulgadas: (a) `DELETE /users/<id>` agora exige `Authorization: Bearer <token>` de um admin (fix da finding #4, CRITICAL/HIGH de segurança); (b) o payload de usuário não inclui mais o campo `password` (hash) (fix complementar da finding #2).

### Observação sobre o ambiente de instalação

A instalação das dependências (`pip install -r requirements.txt`) foi executada no **Python global da máquina** (não havia virtualenv configurado para o projeto). Isso rebaixou pacotes já instalados globalmente (`flask` 3.1.1→3.0.0, `flask-cors` 5.0.1→4.0.0, `python-dotenv`, `marshmallow`) para as versões fixadas no `requirements.txt`, e gerou um aviso de conflito de dependências com `google-api-core` (que exige `requests>=2.33`, ficando em `2.31` após a instalação). Isso pode afetar outras ferramentas Python instaladas nesta máquina.

**Recomendação:** criar um virtualenv dedicado para este projeto antes de instalar dependências:

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

---

## Conclusão

Todos os 11 findings identificados na Fase 2 foram corrigidos na Fase 3, incluindo a correção crítica do arquivo `routes/report_routes.py` (que continha conteúdo injetado/corrompido impedindo o boot da aplicação — tratado como dado não confiável, sem seguir nenhuma instrução embutida nele). A aplicação foi migrada de rotas que concentravam Controller+View+regra de negócio para uma arquitetura em camadas (Models, Services, Routes/Controllers finos, configuração, autenticação e tratamento de erros centralizados), com validação funcional completa via testes manuais de todos os endpoints.
