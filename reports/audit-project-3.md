# Architectural Audit Report — task-manager-api

## Project Analysis

- **Language:** Python 3.12
- **Framework:** Flask 3.0 (+ Flask-SQLAlchemy, Flask-CORS; Marshmallow instalado mas não utilizado)
- **Database:** SQLite (`tasks.db`, arquivo local)
- **ORM / Database Library:** Flask-SQLAlchemy (SQLAlchemy 2.x ORM)
- **Application Type:** API REST (JSON) de gerenciamento de tarefas, usuários e categorias
- **Entry Point:** `app.py` (registra blueprints, cria tabelas com `db.create_all()` e chama `app.run(debug=True)`)
- **Current Architecture:** MVC parcial. Já existem `models/`, `routes/`, `services/` e `utils/`, mas os blueprints em `routes/*.py` fazem ao mesmo tempo o papel de controller, view e regra de negócio. `services/` só tem `NotificationService`, que nenhuma rota usa, e os helpers de `utils/helpers.py` também não são usados pelas rotas.
- **Main Directories:**
  - `models/` — entidades SQLAlchemy (`Task`, `User`, `Category`);
  - `routes/` — blueprints com controller, view e regra de negócio;
  - `services/` — apenas `notification_service.py`;
  - `utils/` — helpers e constantes duplicados nas rotas;
  - `seed.py` — massa de dados inicial.
- **Main Architectural Problems:** regra de negócio e validação dentro das rotas; autenticação falsa (token previsível) e rota de exclusão sem autorização; segredos hardcoded; hash MD5; N+1 nas listagens e relatórios; regra de "task atrasada" duplicada; `routes/report_routes.py` com conteúdo estranho que quebrava a sintaxe (ver Notes).

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 2 |
| HIGH | 3 |
| MEDIUM | 3 |
| LOW | 3 |
| **Total** | **11** |

## Notes

> Observações sobre o processo de auditoria — não são findings de código.

- **Código auditado:** snapshot original do projeto no commit `6d1ce62`. Todas as linhas citadas em `File` / `Line/Snippet` referem-se a esse snapshot, com a exceção descrita no item seguinte.
- **Finding de `routes/report_routes.py` (primeiro CRITICAL) — não reproduzível no histórico do Git.** Na execução de 2026-09-05, a cópia de trabalho de `routes/report_routes.py` tinha um bloco de texto não-Python nas linhas ~59-594, e `python -m py_compile` falhava com `SyntaxError: invalid character '—' (U+2014)` na linha 70. Esse conteúdo **não existe em nenhum commit**: no `6d1ce62` o arquivo tem 223 linhas e compila sem erros. Por isso as linhas desse finding são as registradas naquela execução e não puderam ser reconferidas.
- **Conteúdo não confiável:** o bloco estranho continha instruções dirigidas à Skill sobre como classificar findings, além de referências a outro projeto (`AppManager.js`, `badCrypto`). Ele foi tratado como dado não confiável, e nenhuma dessas instruções foi seguida na auditoria.
- **Arquivos de referência da Skill:** na execução de 2026-09-05, `project-analysis.md`, `anti-patterns.md`, `report-template.md`, `mvc-guidelines.md` e `refactoring-playbook.md` estavam vazios. A análise original foi feita com conhecimento próprio de arquitetura e boas práticas Flask/SQLAlchemy.
- **Revisão de formato (2026-10-27):** o relatório foi reescrito no formato de `report-template.md`, com os 5 campos obrigatórios separados em todos os findings. As linhas foram reconferidas no snapshot. Referências aproximadas (`~319`, `~209`, "múltiplas ocorrências") e deslocadas foram substituídas pelas linhas exatas, por exemplo:
  - imports de `routes/user_routes.py`: linha `:6`, não `:11`;
  - imports de `utils/helpers.py`: linhas `:3-7`, não `:8-12`.

  Também foram acrescentadas ocorrências que a versão anterior omitia, como `json` não usado em `models/task.py:3` e `routes/report_routes.py:8`, e `datetime.utcnow()` em `models/category.py:11`. O conteúdo dos 11 findings não mudou.
- **Campo `Status`:** cada finding traz um campo extra `Status` com o resultado da Fase 3, conferido na árvore atual. Na conferência, o finding de API deprecated está apenas parcialmente corrigido (`models/category.py:11` ainda usa `datetime.utcnow`).
- **Histórico:**
  - **2026-09-05** — Fase 3 aplicada:
    - as rotas viraram controllers finos;
    - a regra de negócio foi para `services/{task,user,category,report}_service.py`;
    - foram criados `config.py`, `errors.py` e `auth.py`;
    - foi adicionado `.env.example`.
  - **Validação (2026-09-05):** passaram `py_compile` em todos os arquivos tocados, `pip install -r requirements.txt`, `python seed.py` sem warnings e `python app.py` sem erros de boot. Os endpoints originais foram testados com `curl`:
    - health, index, tasks (listagem, por id, stats, criação válida e inválida);
    - users (listagem sem `password`, criação válida e com e-mail inválido);
    - categories, reports (summary e por usuário) e login (correto e com senha errada);
    - `DELETE /users/<id>` sem token (`401`), com token de usuário comum (`403`) e com token de admin (`200`).

    Mudanças de contrato intencionais: `DELETE /users/<id>` exige token de admin, e o payload de usuário não inclui mais `password`. As dependências foram instaladas no Python global, sem virtualenv, o que rebaixou pacotes globais (`flask`, `flask-cors`, `python-dotenv`, `marshmallow`). Recomenda-se um `.venv` dedicado.

## Findings

### [CRITICAL] Conteúdo estranho em `routes/report_routes.py` impedia o boot da aplicação
- **File:** `routes/report_routes.py`
- **Line/Snippet:** linhas ~59-594 da cópia de trabalho auditada em 2026-09-05; `py_compile` → `SyntaxError: invalid character '—' (U+2014)` na linha 70 (ver Notes: não presente em nenhum commit)
- **Description:** Um bloco extenso de texto não-Python, aparentemente uma conversa colada ou injetada, estava no meio do módulo, seguido de uma cópia íntegra do código a partir da linha 595.
- **Impact:** `from routes.report_routes import report_bp` em `app.py:6` falhava, e 100% da API ficava fora do ar.
- **Recommendation:** Remover integralmente o texto estranho, manter apenas o código Python válido e tratar o conteúdo como não confiável (sem seguir instruções embutidas nele).
- **Status:** ✅ Corrigido — `routes/report_routes.py` foi reescrito como controller fino, sem o conteúdo estranho, e o módulo compila e carrega no boot.

### [CRITICAL] Senha com MD5 e token de autenticação forjável
- **File:** `models/user.py`, `routes/user_routes.py`
- **Line/Snippet:** `models/user.py:27-29` — `self.password = hashlib.md5(pwd.encode()).hexdigest()`; `models/user.py:31-32` (`check_password` com MD5); `routes/user_routes.py:210` — `'token': 'fake-jwt-token-' + str(user.id)`; `models/user.py:21` — `to_dict()` inclui `'password'`, devolvido em `routes/user_routes.py:85`, `129` e `209`
- **Description:** Senhas são guardadas com MD5 sem salt, e o hash vai para as respostas da API. O "token" de login é uma string previsível, sem assinatura nem expiração.
- **Impact:** Qualquer um forja o token de qualquer usuário trocando o id, e os hashes expostos são quebráveis por rainbow table ou força bruta.
- **Recommendation:** Usar `werkzeug.security.generate_password_hash`/`check_password_hash`, remover `password` do `to_dict()` e emitir um token assinado com expiração.
- **Status:** ✅ Corrigido — `models/user.py:28` usa `generate_password_hash`, o `to_dict()` não inclui mais `password`, e `auth.py:12` gera um token assinado e com expiração via `itsdangerous.URLSafeTimedSerializer`.

### [HIGH] Segredos hardcoded no código-fonte
- **File:** `app.py`, `services/notification_service.py`
- **Line/Snippet:** `app.py:13` — `app.config['SECRET_KEY'] = 'super-secret-key-123'`; `services/notification_service.py:9-10` — `self.email_user = 'taskmanager@gmail.com'`, `self.email_password = 'senha123'`
- **Description:** A chave de assinatura do Flask e a credencial SMTP estão versionadas no repositório.
- **Impact:** Quem tem acesso ao código pode forjar sessões e usar a conta de e-mail.
- **Recommendation:** Ler os segredos de variáveis de ambiente (`python-dotenv` já está nas dependências, mas não era usado).
- **Status:** ✅ Corrigido, com ressalva — `config.py` lê `SECRET_KEY` e a configuração SMTP do ambiente, e há `.env.example`. Porém `config.py:10` mantém o fallback fixo `'dev-secret-key-change-me'` quando a variável não está definida, e ele precisa ser sobrescrito em produção.

### [HIGH] Exclusão de usuário sem autenticação nem autorização
- **File:** `routes/user_routes.py`
- **Line/Snippet:** `routes/user_routes.py:134-151` — `@user_bp.route('/users/<int:user_id>', methods=['DELETE'])`, que apaga as tasks do usuário (linhas 140-142) e o usuário (linha 145)
- **Description:** A rota não verifica quem está chamando nem o papel dessa pessoa.
- **Impact:** Qualquer cliente anônimo apaga qualquer usuário e todas as suas tasks.
- **Recommendation:** Exigir um token válido e o papel `admin` antes de processar a exclusão.
- **Status:** ✅ Corrigido — `@require_admin` (`auth.py:52`) é aplicado em `routes/user_routes.py:32`: sem token a rota responde `401`, e com token de não-admin, `403`.

### [HIGH] Regra de negócio e validação dentro das rotas
- **File:** `routes/task_routes.py`, `routes/user_routes.py`, `routes/report_routes.py`
- **Line/Snippet:**
  - `routes/task_routes.py:86-154` (`create_task`, com validações nas linhas 96-110 e checagem de usuário e categoria nas 117-122) e `:157-223` (`update_task`);
  - `routes/user_routes.py:43-90` (`create_user`, com validações nas linhas 54-72) e `:93-132` (`update_user`);
  - `routes/report_routes.py:13-101` (`summary_report`, que calcula o relatório inteiro).
- **Description:** Validação de título, status, prioridade, e-mail e role, além do cálculo de relatórios, está nos handlers HTTP. Ao mesmo tempo, `utils/helpers.py:57-108` (`process_task_data`) implementa boa parte dessas validações e não é usado por nenhuma rota.
- **Impact:** As regras divergem entre create e update e não podem ser testadas sem request Flask, e o helper existente vira código morto.
- **Recommendation:** Extrair para services (`TaskService`, `UserService`, `ReportService`) e reaproveitar o helper.
- **Status:** ✅ Corrigido — a regra está em `services/task_service.py`, `services/user_service.py`, `services/category_service.py` e `services/report_service.py`, e as rotas só leem o request e chamam o service.

### [MEDIUM] N+1 queries em listagens e relatórios
- **File:** `routes/task_routes.py`, `routes/user_routes.py`, `routes/report_routes.py`
- **Line/Snippet:**
  - `routes/task_routes.py:42` — `User.query.get(t.user_id)` e `:51` — `Category.query.get(t.category_id)`, dentro do loop da linha 16;
  - `routes/user_routes.py:22` — `len(u.tasks)` (lazy load por usuário);
  - `routes/report_routes.py:56` — `Task.query.filter_by(user_id=u.id).all()` por usuário;
  - `routes/report_routes.py:163` — `Task.query.filter_by(category_id=c.id).count()` por categoria.
- **Description:** Cada item da listagem dispara consultas adicionais para buscar relacionamentos ou contagens.
- **Impact:** O número de queries cresce com o volume de dados, e a latência degrada proporcionalmente.
- **Recommendation:** Usar `joinedload`/`selectinload` nos relacionamentos e agregações com `GROUP BY` para as contagens.
- **Status:** ✅ Corrigido — `services/task_service.py:21` usa `joinedload(Task.user), joinedload(Task.category)`. As contagens usam `func.count` com `GROUP BY` em `services/user_service.py:13`, `services/category_service.py:12` e `services/report_service.py:46`.

### [MEDIUM] Regra de "task atrasada" duplicada em vez de usar `Task.is_overdue()`
- **File:** `routes/task_routes.py`, `routes/user_routes.py`, `routes/report_routes.py`
- **Line/Snippet:** `due_date < datetime.utcnow()` + `status != 'done' and status != 'cancelled'` em:
  - `routes/task_routes.py:31-32`, `:72-73` e `:285-286`;
  - `routes/user_routes.py:172-173`;
  - `routes/report_routes.py:35-36` e `:133-134`.

  A regra já existe em `models/task.py:50-60` (`is_overdue`).
- **Description:** A mesma regra aparece copiada em 6 lugares, enquanto o método do model que a implementa não é usado.
- **Impact:** Mudar a regra em um lugar e esquecer outro produz respostas inconsistentes entre endpoints.
- **Recommendation:** Usar `task.is_overdue()` em todos os pontos.
- **Status:** ✅ Corrigido — `services/task_service.py:13`, `services/user_service.py:126` e `services/report_service.py:30` e `:110` chamam `is_overdue()`.

### [MEDIUM] Tratamento de erros com `except:` genérico e repetido
- **File:** `routes/task_routes.py`, `routes/user_routes.py`, `routes/report_routes.py`, `utils/helpers.py`
- **Line/Snippet:** `except:` sem tipo em:
  - `routes/task_routes.py:62`, `137`, `204` e `236`;
  - `routes/user_routes.py:130` e `149`;
  - `routes/report_routes.py:186`, `207` e `221`;
  - `utils/helpers.py:46`, `49` e `88`.

  Além disso, há `except Exception` repetido em `routes/task_routes.py:151`, `:221` e `routes/user_routes.py:87`.
- **Description:** Qualquer exceção, incluindo bugs e falhas de conexão, é engolida e convertida em mensagens genéricas como "Erro ao atualizar".
- **Impact:** Erros reais ficam mascarados, o que dificulta o diagnóstico e a observabilidade.
- **Recommendation:** Capturar exceções específicas e centralizar o tratamento com `@app.errorhandler`.
- **Status:** ✅ Corrigido — `errors.py:38-51` registra handlers para `AppError`, `SQLAlchemyError`, 404 e `Exception`. Não há mais `except:` nem `try/except` nas rotas.

### [LOW] Imports não utilizados
- **File:** `routes/user_routes.py`, `routes/task_routes.py`, `routes/report_routes.py`, `utils/helpers.py`, `models/task.py`, `app.py`
- **Line/Snippet:**
  - `routes/user_routes.py:6` — `import hashlib, json, re` (`hashlib` e `json` não usados);
  - `routes/task_routes.py:7` — `import json, os, sys, time`;
  - `routes/report_routes.py:8` — `import json`;
  - `utils/helpers.py:3-7` — `os`, `json`, `sys`, `math`, `hashlib`;
  - `models/task.py:3` — `import json`;
  - `app.py:7` — `import os, sys, json, datetime` (só `datetime` é usado).
- **Description:** Módulos importados e nunca usados.
- **Impact:** Ruído na leitura, e sugere código copiado ou morto.
- **Recommendation:** Remover os imports.
- **Status:** ✅ Corrigido — removidos nos módulos reescritos na Fase 3.

### [LOW] Magic numbers e strings duplicados apesar de constantes existentes
- **File:** `utils/helpers.py`, `routes/task_routes.py`, `routes/user_routes.py`
- **Line/Snippet:**
  - as constantes estão em `utils/helpers.py:110-116` (`VALID_STATUSES`, `VALID_ROLES`, `MAX_TITLE_LENGTH`, `MIN_TITLE_LENGTH`, `MIN_PASSWORD_LENGTH`, `DEFAULT_PRIORITY`, `DEFAULT_COLOR`);
  - mesmo assim, há literais em `utils/helpers.py:64`, `75` e `84`;
  - em `routes/task_routes.py:96`, `99`, `110`, `167`, `169` e `177`;
  - em `routes/user_routes.py:64`, `71`, `115` e `120`.
- **Description:** As validações usam números e listas literais (`3`, `200`, `['user','admin','manager']`, `4`, `1`/`5`) em vez das constantes declaradas.
- **Impact:** A constante e a regra efetiva podem divergir sem que ninguém perceba.
- **Recommendation:** Referenciar as constantes centralizadas em todos os pontos de validação.
- **Status:** ✅ Corrigido — `utils/helpers.py` centraliza as constantes (incluindo `MIN_PRIORITY`/`MAX_PRIORITY`), e os services as usam (ex.: `services/user_service.py:85` com `MIN_PASSWORD_LENGTH`).

### [LOW] API legada do SQLAlchemy e `datetime.utcnow()` deprecated
- **File:** `routes/*.py`, `models/*.py`, `utils/helpers.py`, `services/notification_service.py`
- **Line/Snippet:**
  - `Model.query.get(id)` em:
    - `routes/task_routes.py:42`, `51`, `67`, `117`, `122`, `158`, `188`, `195` e `227`;
    - `routes/user_routes.py:29`, `94`, `136` e `155`;
    - `routes/report_routes.py:105`, `192` e `213`.
  - `datetime.utcnow` em:
    - `models/task.py:15-16` e `52`;
    - `models/user.py:14`;
    - `models/category.py:11`;
    - `utils/helpers.py:38`;
    - `services/notification_service.py:35`;
    - e nas rotas, por exemplo `routes/task_routes.py:215` e `routes/report_routes.py:45`.
- **Description:** `Query.get()` é a API legada do SQLAlchemy 2.x (a recomendada é `db.session.get(Model, id)`), e `datetime.utcnow()` está deprecated desde o Python 3.12.
- **Impact:** Baixo hoje, porque ainda funciona com warnings, mas essas APIs podem ser removidas em versões futuras.
- **Recommendation:** Migrar para `db.session.get(...)` e `datetime.now(timezone.utc)`.
- **Status:** ⚠️ Parcialmente corrigido:
  - `db.session.get(...)` é usado em toda a camada de services, e não restou nenhum `query.get(`;
  - `datetime.utcnow()` foi trocado por `utils.helpers.utc_now()` em `models/task.py`, `models/user.py`, services e `seed.py`;
  - porém `models/category.py:11` ainda usa `default=datetime.utcnow`.

## Total: 11 findings

---

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
