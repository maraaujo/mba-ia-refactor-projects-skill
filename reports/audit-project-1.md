# Architectural Audit Report — code-smells-project

## Project Analysis

- **Language:** Python 3
- **Framework:** Flask 3.1.1 (+ flask-cors 5.0.1) — `requirements.txt:1-2`
- **Database:** SQLite (`loja.db`, criado no primeiro boot)
- **ORM / Database Library:** Nenhum ORM — driver nativo `sqlite3`, SQL escrito à mão
- **Application Type:** API REST monolítica de e-commerce (produtos, usuários, pedidos, relatório de vendas, health check, 2 rotas administrativas) — 19 endpoints
- **Entry Point:** `app.py` (`app.run(...)` em `app.py:88`)
- **Current Architecture:** Monolito plano, sem diretórios. `app.py` registra rotas e também contém handlers administrativos com SQL direto; `controllers.py` mistura parsing HTTP, validação e regra de negócio; `models.py` mistura SQL concatenado, regras de pedido/estoque e cálculo de desconto; `database.py` mantém uma conexão global e também cria schema e seed.
- **Main Directories:** nenhum — todos os módulos na raiz (`app.py`, `controllers.py`, `models.py`, `database.py`)
- **Main Architectural Problems:** SQL Injection sistêmico em `models.py`; endpoint de execução arbitrária de SQL; endpoints administrativos sem autenticação; segredos hardcoded e expostos via `/health`; senhas em texto plano; conexão global compartilhada entre threads; regras de negócio espalhadas entre controller e model; N+1 na listagem de pedidos.

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 5 |
| HIGH | 6 |
| MEDIUM | 7 |
| LOW | 5 |
| **Total** | **23** |

## Notes

> Observações sobre o processo de auditoria — não são findings de código.

- **Código auditado:** snapshot original do projeto no commit `6d1ce62` (boilerplate do desafio, antes de qualquer alteração). Todos os arquivos e linhas citados em `File` / `Line/Snippet` referem-se a esse snapshot; vários deles (`models.py`, `controllers.py`) não existem mais na árvore atual porque foram substituídos na Fase 3. O commit `1604715` não foi usado porque contém comentários de auditoria escritos à mão dentro do código, o que enviesaria a análise.
- **Re-execução (2026-09-29):** as Fases 1 e 2 foram executadas de novo depois do reforço da regra de campos obrigatórios em todas as severidades (`SKILL.md` Fase 2, `report-template.md` regra 3). A versão anterior deste relatório trazia os 17 findings HIGH/MEDIUM/LOW apenas com título e status.
- **Campo `Status`:** a Fase 3 já foi aplicada em 2026-09-05. Cada finding traz um campo extra `Status` que descreve o estado na árvore atual, verificado contra o código de hoje, não copiado do relatório anterior. Esse campo não substitui nenhum dos cinco campos obrigatórios.
- **Diferenças em relação ao relatório anterior:**
  - novo finding **H6** (quantidade de itens do pedido não validada), que a auditoria anterior não havia registrado e que continua aberto no código atual;
  - **M1** e **M6** passaram de "corrigido" para "parcialmente corrigido" após verificação no código atual.
- **Histórico:**
  - **2026-09-05** — Fase 3 aplicada: reestruturação para MVC + Service layer.
  - **2026-09-05 (ajuste)** — `POST /admin/query` restaurado como rota inerte (410 Gone) para preservar o contrato dos 19 endpoints; validado com payload `DROP TABLE`.

## Findings

### [CRITICAL] C1 — SQL Injection por concatenação de strings em toda a camada de dados
- **File:** `models.py`
- **Line/Snippet:** linhas 28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 148-151, 155, 157-166, 174, 188, 192, 220, 224, 280, 289-297. Exemplos:
  ```python
  # models.py:109-111
  cursor.execute(
      "SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"
  )
  # models.py:291
  query += " AND (nome LIKE '%" + termo + "%' OR descricao LIKE '%" + termo + "%')"
  ```
- **Description:** Nenhuma query usa placeholders; valores são concatenados diretamente na string SQL. Vários desses valores vêm do cliente sem qualquer tratamento: `email`/`senha` do corpo de `POST /login` (`controllers.py:170-171`), `q`/`categoria` da query string de `GET /produtos/busca` (`controllers.py:113-114`), `nome`/`descricao` de `POST /produtos` e `POST /usuarios`, e `produto_id`/`quantidade` dos itens de `POST /pedidos`, que não têm checagem de tipo. Os IDs vindos da URL (`<int:id>`) são convertidos pelo Flask e têm exploração limitada, mas seguem o mesmo padrão inseguro.
- **Impact:** Bypass de autenticação (`email = "' OR '1'='1' --"` autentica como o primeiro usuário, o admin), exfiltração de qualquer tabela via `UNION` na busca de produtos, e alteração ou corrupção de dados pelos endpoints de escrita.
- **Recommendation:** Reescrever todas as queries com parâmetros do driver (`cursor.execute("... WHERE email = ?", (email,))`). Na busca dinâmica, montar a cláusula `WHERE` por partes, mas passar sempre os valores em uma lista de parâmetros (`LIKE ?` com `f"%{termo}%"` como parâmetro).
- **Status:** ✅ Corrigido — `models/*.py` usam apenas `?`. A única concatenação restante (`models/pedido_model.py:65`) junta duas strings SQL fixas, sem entrada do usuário.

### [CRITICAL] C2 — Execução arbitrária de SQL vindo do cliente (`POST /admin/query`)
- **File:** `app.py`
- **Line/Snippet:** linhas 59-78
  ```python
  query = dados.get("sql", "")      # app.py:62
  ...
  cursor.execute(query)             # app.py:69
  ```
- **Description:** O endpoint lê o campo `sql` do corpo da requisição e o executa sem whitelist, autenticação ou restrição de comando. Comandos que não começam com `SELECT` são commitados (`app.py:75`). Além disso, `str(e)` devolve a mensagem de erro do SQLite ao cliente (`app.py:78`).
- **Impact:** Qualquer cliente anônimo tem controle total do banco: pode ler todas as tabelas (incluindo senhas em texto plano), alterar dados ou executar `DROP TABLE`.
- **Recommendation:** Remover a funcionalidade. Se houver necessidade real de operações administrativas, expô-las como operações específicas, autenticadas e auditáveis, nunca como SQL livre.
- **Status:** ⚠️ Neutralizado, com a rota preservada — `controllers/admin_controller.py:13-24` não lê o corpo nem executa SQL e responde sempre `410 Gone`. Rota registrada em `routes.py:48-50`.

### [CRITICAL] C3 — Endpoint destrutivo sem autenticação (`POST /admin/reset-db`)
- **File:** `app.py`
- **Line/Snippet:** linhas 47-57
  ```python
  @app.route("/admin/reset-db", methods=["POST"])
  def reset_database():
      ...
      cursor.execute("DELETE FROM usuarios")
  ```
- **Description:** A rota apaga todas as tabelas (`itens_pedido`, `pedidos`, `produtos`, `usuarios`) sem exigir autenticação, token ou qualquer confirmação.
- **Impact:** Qualquer requisição anônima apaga todos os dados da aplicação, e o dano é irreversível sem backup.
- **Recommendation:** Proteger a rota com autenticação administrativa (token ou sessão com papel `admin`), bloqueá-la por padrão quando não houver credencial configurada e mover o SQL para a camada de dados.
- **Status:** ✅ Corrigido — protegido por `middleware.admin_required` (`middleware.py:8-21`), que exige o header `X-Admin-Token` igual a `ADMIN_TOKEN`. Sem essa variável configurada, o endpoint responde 403.

### [CRITICAL] C4 — SECRET_KEY hardcoded e exposta publicamente em `/health`
- **File:** `app.py`, `controllers.py`
- **Line/Snippet:** `app.py:7` e `controllers.py:285-289`
  ```python
  app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"   # app.py:7
  ...
  "db_path": "loja.db",                                        # controllers.py:287
  "debug": True,
  "secret_key": "minha-chave-super-secreta-123"                # controllers.py:289
  ```
- **Description:** A chave usada pelo Flask para assinar sessões está versionada no código e, além disso, é devolvida literalmente no JSON do `GET /health`, junto com o caminho do banco, o ambiente e o estado de debug.
- **Impact:** Quem tem a chave pode forjar cookies de sessão assinados. A resposta do `/health` também entrega a um atacante informações de reconhecimento (debug ativo, arquivo de banco).
- **Recommendation:** Ler `SECRET_KEY` de variável de ambiente (sem valor default real), rotacionar a chave exposta e limitar o `/health` a status e conectividade.
- **Status:** ✅ Corrigido — `config.py:8` lê `SECRET_KEY` do ambiente (ou gera uma aleatória, com warning em `app.py:18-22`). `services/health_service.py:6-16` não retorna mais segredos, `debug`, `ambiente` nem `db_path`.

### [CRITICAL] C5 — Senhas armazenadas em texto plano e devolvidas pela API
- **File:** `database.py`, `models.py`
- **Line/Snippet:** `database.py:31` (coluna `senha TEXT`), `database.py:75-79` (seed com `"admin123"`, `"123456"`, `"senha123"`), `models.py:83` e `models.py:99` (`"senha": row["senha"]`), `models.py:110` (comparação direta no SQL), `models.py:127-128` (insert em texto plano)
- **Description:** Senhas são gravadas e comparadas em texto plano. `get_todos_usuarios` e `get_usuario_por_id` incluem o campo `senha` no dicionário retornado, então `GET /usuarios` e `GET /usuarios/<id>` expõem a senha de todos os usuários.
- **Impact:** Vazamento imediato das credenciais de todos os usuários, inclusive do admin, a qualquer cliente anônimo. Em caso de vazamento do banco, as senhas ficam utilizáveis sem nenhum esforço (e costumam ser reutilizadas em outros serviços).
- **Recommendation:** Armazenar apenas hash com salt (`werkzeug.security.generate_password_hash` / `check_password_hash`), buscar o usuário por e-mail e verificar o hash na aplicação, e nunca incluir `senha` nas respostas.
- **Status:** ✅ Corrigido — hash em `services/usuario_service.py:33` e no seed (`schema.py:84`), verificação em `services/usuario_service.py:44`, respostas públicas sem `senha` via `models/usuario_model.py:6` (`_row_para_dict_publico`).

### [HIGH] H1 — Modo debug ativo e servidor exposto em todas as interfaces
- **File:** `app.py`
- **Line/Snippet:** `app.py:8` e `app.py:88`
  ```python
  app.config["DEBUG"] = True                              # app.py:8
  app.run(host="0.0.0.0", port=5000, debug=True)          # app.py:88
  ```
- **Description:** O debug está fixo como `True` no código, e o servidor escuta em `0.0.0.0`. Com isso, o debugger interativo do Werkzeug e os stack traces completos ficam acessíveis pela rede.
- **Impact:** Stack traces vazam código e caminhos internos. O console do debugger (protegido só por PIN) permite execução de código Python no servidor se o PIN for obtido ou deduzido.
- **Recommendation:** Controlar debug por variável de ambiente com padrão `false` e nunca usar o servidor de desenvolvimento em produção.
- **Status:** ✅ Corrigido — `config.py:9` (`FLASK_DEBUG`, padrão `false`), usado em `app.py:58`.

### [HIGH] H2 — Acesso direto ao banco nas camadas de roteamento e controller
- **File:** `app.py`, `controllers.py`
- **Line/Snippet:** `app.py:49-55` e `app.py:66-75` (`get_db()` + `cursor.execute` dentro dos handlers de rota); `controllers.py:3` (`from database import get_db`) e `controllers.py:266-274` (`health_check` executa 4 queries)
- **Description:** Os handlers administrativos em `app.py` e o `health_check` em `controllers.py` abrem cursor e executam SQL diretamente, ignorando a camada `models.py` que as demais rotas usam.
- **Impact:** A camada de dados fica dividida entre três arquivos, e mudanças de schema precisam ser procuradas fora do model. Também impede testar controllers sem banco real.
- **Recommendation:** Mover o SQL para funções na camada de dados (`models`/`database`) e fazer handlers e controllers apenas chamarem essas funções, via service quando houver regra.
- **Status:** ✅ Corrigido — reset em `database.py:41-49`, chamado por `controllers/admin_controller.py:7-10`; contagens do health em `models/*` (`contar_*`), orquestradas por `services/health_service.py`.

### [HIGH] H3 — Regras de negócio implementadas nos controllers
- **File:** `controllers.py`
- **Line/Snippet:** `controllers.py:43-54` (regras de preço, estoque, tamanho de nome e categorias válidas), `controllers.py:208-210` (disparo de notificações de pedido), `controllers.py:247-250` (reação à mudança de status)
  ```python
  if preco < 0:                                            # controllers.py:43
      return jsonify({"erro": "Preço não pode ser negativo"}), 400
  ...
  print("ENVIANDO EMAIL: Pedido " + str(resultado["pedido_id"]) + ...)   # controllers.py:208
  ```
- **Description:** Os controllers fazem mais do que traduzir request/response: aplicam regras de domínio do produto e orquestram efeitos colaterais do pedido (e-mail, SMS, push, notificação de aprovação/cancelamento).
- **Impact:** As regras não podem ser reutilizadas nem testadas sem o contexto HTTP, e cada novo ponto de entrada precisaria duplicá-las. Isso já acontece em `atualizar_produto` (ver M3).
- **Recommendation:** Extrair validação e orquestração para uma camada de serviço. O controller deve apenas parsear a entrada, chamar o serviço e montar a resposta.
- **Status:** ✅ Corrigido — validação em `services/produto_service.py:15-42`, notificações em `services/pedido_service.py:31-34` e `:71-74`. Os controllers atuais (`controllers/*.py`) só fazem parsing e resposta.

### [HIGH] H4 — Regras de negócio implementadas na camada de dados
- **File:** `models.py`
- **Line/Snippet:** `models.py:137-146` (verificação de estoque e cálculo do total do pedido), `models.py:163-166` (baixa de estoque), `models.py:256-262` (faixas de desconto do relatório)
  ```python
  desconto = 0                        # models.py:256
  if faturamento > 10000:
      desconto = faturamento * 0.1
  elif faturamento > 5000:
  ```
- **Description:** `criar_pedido` decide se o pedido é válido e calcula o total, e `relatorio_vendas` define a política comercial de desconto. São regras de domínio misturadas ao SQL.
- **Impact:** Mudar a política de desconto ou a regra de estoque exige mexer no módulo de persistência, e essas regras não podem ser testadas sem banco. Também alimenta a God-module `models.py` (314 linhas cobrindo 3 domínios).
- **Recommendation:** Deixar no model apenas leitura e escrita parametrizadas e mover cálculo de total, validação de estoque e desconto para services.
- **Status:** ✅ Corrigido — `services/pedido_service.py:10-28` (itens e total) e `services/relatorio_service.py:15-22` (desconto). `models/pedido_model.py` contém apenas queries.

### [HIGH] H5 — Conexão de banco global e mutável compartilhada entre threads
- **File:** `database.py`
- **Line/Snippet:** `database.py:4` e `database.py:8-10`
  ```python
  db_connection = None                                                   # database.py:4
  ...
  global db_connection
  if db_connection is None:
      db_connection = sqlite3.connect(db_path, check_same_thread=False)  # database.py:10
  ```
- **Description:** Uma única conexão, guardada em variável de módulo, atende todas as requisições. `check_same_thread=False` desliga a proteção do `sqlite3` contra uso concorrente. Todas as requisições compartilham também a mesma transação.
- **Impact:** Transações de requisições diferentes se misturam. Se `criar_pedido` falhar no meio das escritas (`models.py:148-166`, sem rollback), as linhas parciais continuam pendentes e são gravadas pelo próximo `db.commit()` de outra requisição. Requisições concorrentes também podem corromper o estado do cursor.
- **Recommendation:** Abrir uma conexão por requisição (`flask.g` + `teardown_appcontext`) ou usar um pool, e tratar cada operação de negócio como uma transação com commit/rollback explícito.
- **Status:** ✅ Corrigido (estado global) — `database.py:15-25` usa `flask.g` e fecha a conexão no teardown. ⚠️ Observação: no código atual, `models/pedido_model.py:76` e `:87` fazem commit a cada insert, então `pedido_service.criar_pedido` não é atômico (uma falha entre os inserts deixa pedido sem itens ou estoque não baixado).

### [HIGH] H6 — Quantidade e tipos dos itens de pedido não são validados
- **File:** `controllers.py`, `models.py`
- **Line/Snippet:** `controllers.py:195-201` (só checa presença de `usuario_id` e `itens`), `models.py:144-146` e `models.py:163-166`
  ```python
  if produto["estoque"] < item["quantidade"]:                       # models.py:144
      return {"erro": "Estoque insuficiente para " + produto["nome"]}
  total = total + (produto["preco"] * item["quantidade"])           # models.py:146
  ...
  "UPDATE produtos SET estoque = estoque - " + str(item["quantidade"]) +   # models.py:164
  ```
- **Description:** `quantidade` nunca é validada como inteiro positivo. Uma quantidade negativa passa na checagem de estoque, gera `total` negativo e, no `UPDATE`, *aumenta* o estoque. Valores não numéricos (`"abc"`) causam `TypeError`, que vira HTTP 500. Em produtos, o mesmo vale para `preco`/`estoque` (`controllers.py:43-46`): uma string provoca `TypeError` em vez de 400.
- **Impact:** Qualquer cliente pode criar pedidos com valor negativo (o faturamento do relatório fica errado) e inflar o estoque arbitrariamente, contornando a regra de estoque.
- **Recommendation:** Validar no service, antes de qualquer leitura ou escrita, que `produto_id` é inteiro e `quantidade` é inteiro `>= 1`, e que `preco`/`estoque` são numéricos, retornando 400 com mensagem clara.
- **Status:** ❌ Não corrigido — a mesma lógica sem validação continua em `services/pedido_service.py:14-21`, e `services/produto_service.py:31-34` segue sem checagem de tipo.

### [MEDIUM] M1 — N+1 queries na listagem e na criação de pedidos
- **File:** `models.py`
- **Line/Snippet:** `models.py:177-200` (`get_pedidos_usuario`) e `models.py:209-232` (`get_todos_pedidos`); também `models.py:139-141` e `models.py:154-156` (`criar_pedido`)
  ```python
  for row in rows:                                                    # models.py:209
      cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"]))
      for item in itens:
          cursor3.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
  ```
- **Description:** Para cada pedido, o código faz uma query de itens e, para cada item, outra query de produto: `1 + P + I` consultas por listagem. Em `criar_pedido`, cada produto é buscado duas vezes (uma na validação, outra no insert).
- **Impact:** O custo de `GET /pedidos` cresce linearmente com o número de pedidos e itens, e o endpoint degrada rápido com volume real.
- **Recommendation:** Uma única query com `LEFT JOIN` entre pedidos, itens e produtos, agrupada em memória. Na criação, buscar todos os produtos do pedido de uma vez (`WHERE id IN (...)`) e reaproveitar o resultado.
- **Status:** ⚠️ Parcialmente corrigido — as listagens usam uma única query com JOIN (`models/pedido_model.py:35-66`). A criação ainda faz uma query por item (`services/pedido_service.py:14-15`), mas não repete mais a busca na fase de insert.

### [MEDIUM] M2 — Duplicação entre `get_pedidos_usuario` e `get_todos_pedidos`
- **File:** `models.py`
- **Line/Snippet:** `models.py:171-201` vs. `models.py:203-233` (idênticos, exceto pelo `WHERE usuario_id` na linha 174). O mapeamento linha→dict de produto também se repete em `models.py:12-21`, `31-40` e `304-313`.
- **Description:** A montagem do pedido com itens, incluindo o N+1, foi copiada linha a linha nas duas funções, e o mapeamento de produto aparece três vezes.
- **Impact:** Qualquer correção (como a do N+1 ou um novo campo no pedido) precisa ser aplicada em dois ou três lugares, com risco real de as versões divergirem.
- **Recommendation:** Uma função base com filtro opcional e um helper único de mapeamento de linha.
- **Status:** ✅ Corrigido — `_QUERY_PEDIDOS_COM_ITENS` + `_montar_pedidos_a_partir_das_linhas` (`models/pedido_model.py:6-66`) são reutilizados pelas duas consultas.

### [MEDIUM] M3 — Validação de produto duplicada e divergente entre criar e atualizar
- **File:** `controllers.py`
- **Line/Snippet:** `controllers.py:28-54` (`criar_produto`) vs. `controllers.py:72-90` (`atualizar_produto`)
- **Description:** O bloco de validação foi copiado e já divergiu: `atualizar_produto` não verifica o tamanho do nome (`controllers.py:47-50`) nem a categoria (`controllers.py:52-54`).
- **Impact:** `PUT /produtos/<id>` aceita nome de 1 caractere, nome acima de 200 caracteres e categoria inexistente, gravando dados que `POST /produtos` rejeitaria.
- **Recommendation:** Uma única função de validação usada por criação e atualização.
- **Status:** ✅ Corrigido — `services/produto_service.py:15-42` (`_validar_dados_produto`) é chamada por `criar_produto` e `atualizar_produto`.

### [MEDIUM] M4 — Ausência de integridade referencial no schema
- **File:** `database.py`
- **Line/Snippet:** `database.py:36-53`
  ```sql
  usuario_id INTEGER,      -- database.py:39
  pedido_id INTEGER,       -- database.py:48
  produto_id INTEGER,      -- database.py:49
  ```
- **Description:** `pedidos.usuario_id`, `itens_pedido.pedido_id` e `itens_pedido.produto_id` não têm `REFERENCES` nem `NOT NULL`. `criar_pedido` aceita qualquer `usuario_id` (`controllers.py:195-199`), e `deletar_produto` (`models.py:68`) remove produtos referenciados por itens.
- **Impact:** Pedidos órfãos para usuários inexistentes, e itens apontando para produtos apagados (que aparecem como `"Desconhecido"` em `models.py:196`).
- **Recommendation:** Declarar chaves estrangeiras e `NOT NULL`, e habilitar `PRAGMA foreign_keys = ON` em cada conexão (desligado por padrão no SQLite).
- **Status:** ✅ Corrigido — `REFERENCES` + `NOT NULL` em `schema.py:34`, `:44-45`, e `PRAGMA foreign_keys = ON` em `database.py:11`.

### [MEDIUM] M5 — Tratamento de erros repetitivo, inconsistente e com vazamento de detalhes
- **File:** `controllers.py`, `app.py`, `models.py`
- **Line/Snippet:** `except Exception as e: return jsonify({"erro": str(e)}), 500` em todos os handlers de `controllers.py` (ex.: linhas 10-12, 21-22, 60-62, 95-96, 291-292) e em `app.py:77-78`; `controllers.py:169-170` (`dados.get` com `dados` possivelmente `None`); `models.py:143` e `:145` (erro retornado como dict)
- **Description:** Cada rota repete o mesmo `try/except` genérico, que devolve a mensagem crua da exceção ao cliente. O formato do erro varia: `{"erro": ...}` na maioria, `{"status": "erro", "detalhes": ...}` no health (`controllers.py:292`) e dict `{"erro": ...}` retornado pelo model em vez de exceção. Em `login` e `atualizar_status_pedido` (`controllers.py:240`), um corpo ausente gera `AttributeError`, que vira 500 em vez de 400.
- **Impact:** Mensagens internas do SQLite e do Python chegam ao cliente e ajudam a explorar o C1. Clientes não conseguem tratar erros de forma uniforme, e erros de entrada aparecem como falhas do servidor.
- **Recommendation:** Exceções de domínio (`ValidationError`, `NotFoundError`, ...) e um error handler global que mapeia cada uma para status HTTP e resposta padronizada, com uma mensagem genérica para erros inesperados.
- **Status:** ✅ Corrigido — `errors.py:4-48` (hierarquia `AppError` + handlers globais, 500 genérico com log). Os controllers atuais não têm `try/except` e usam `get_json(silent=True)`.

### [MEDIUM] M6 — CORS aberto para qualquer origem
- **File:** `app.py`
- **Line/Snippet:** `app.py:9` — `CORS(app)`
- **Description:** O `flask-cors` sem argumentos libera todas as origens (`*`) para todas as rotas, incluindo as administrativas.
- **Impact:** Qualquer site pode chamar a API a partir do navegador de um visitante. Somado a C2/C3, isso permite atacar a API a partir de páginas de terceiros.
- **Recommendation:** Restringir as origens a uma lista configurável por ambiente.
- **Status:** ⚠️ Parcialmente corrigido — `CORS_ORIGINS` é configurável (`config.py:11`, `app.py:28`), mas o padrão continua `*` para preservar o contrato. Precisa ser definido em produção.

### [MEDIUM] M7 — Magic strings de status de pedido espalhadas pelo código
- **File:** `controllers.py`, `models.py`, `database.py`
- **Line/Snippet:** `controllers.py:242` (lista inline de status), `controllers.py:247` e `:249`; `models.py:150`, `:247`, `:250`, `:253`; `database.py:40` (`DEFAULT 'pendente'`)
- **Description:** Os valores `"pendente"`, `"aprovado"`, `"enviado"`, `"entregue"` e `"cancelado"` são literais repetidos em três arquivos, sem uma fonte única.
- **Impact:** Renomear ou acrescentar um status exige caçar literais, e um erro de digitação em qualquer ponto passa silenciosamente (por exemplo, o relatório deixa de contar um status).
- **Recommendation:** Centralizar os status em um módulo de constantes (ou `Enum`) e referenciá-lo em validação, persistência e relatório.
- **Status:** ✅ Corrigido — `constants.py:6-9`, usado em `services/pedido_service.py` e `services/relatorio_service.py`.

### [LOW] L1 — Imports não utilizados
- **File:** `database.py`, `models.py`
- **Line/Snippet:** `database.py:2` — `import os`; `models.py:2` — `import sqlite3`
- **Description:** Nenhum dos dois módulos usa o import declarado.
- **Impact:** Ruído na leitura e falsa sugestão de dependência (por exemplo, que `database.py` lê variáveis de ambiente, o que não faz).
- **Recommendation:** Remover os imports não usados e adotar um linter (`pyflakes`/`ruff`) para evitar recorrência.
- **Status:** ✅ Corrigido — os módulos reescritos não contêm esses imports.

### [LOW] L2 — Caminho do banco hardcoded
- **File:** `database.py`, `controllers.py`
- **Line/Snippet:** `database.py:5` — `db_path = "loja.db"`; `controllers.py:287` — `"db_path": "loja.db"`
- **Description:** O caminho do arquivo SQLite é fixo no código, relativo ao diretório de execução, e repetido como literal no health check.
- **Impact:** Não é possível usar outro banco por ambiente (testes, produção). O banco é criado onde quer que o processo seja iniciado.
- **Recommendation:** Ler o caminho de variável de ambiente com default, em um módulo de configuração.
- **Status:** ✅ Corrigido — `config.py:10` (`DATABASE_PATH`), consumido em `database.py:18`.

### [LOW] L3 — Magic numbers em validação e regra de desconto
- **File:** `controllers.py`, `models.py`
- **Line/Snippet:** `controllers.py:47` (`len(nome) < 2`), `controllers.py:49` (`len(nome) > 200`); `models.py:257-262` (`10000`, `5000`, `1000`, `0.1`, `0.05`, `0.02`)
- **Description:** Limites de negócio aparecem como literais sem nome, então não fica claro o que representam nem onde mais são usados.
- **Impact:** Ajustar um limite exige encontrar o literal certo, e a ausência do limite em `atualizar_produto` (M3) passou despercebida justamente por não haver uma constante compartilhada.
- **Recommendation:** Constantes nomeadas em módulo único.
- **Status:** ✅ Corrigido — `constants.py:11-19`, usadas em `services/produto_service.py:35-38` e `services/relatorio_service.py:15-22`.

### [LOW] L4 — `print()` usado como logging, incluindo dados pessoais
- **File:** `controllers.py`, `app.py`
- **Line/Snippet:** `controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250`; `app.py:56, 83-86`
  ```python
  print("Login falhou: " + email)      # controllers.py:182
  ```
- **Description:** Toda a instrumentação usa `print`, sem nível, timestamp ou origem. E-mails de usuários são escritos na saída padrão em cadastro e login (`controllers.py:161`, `:179`, `:182`).
- **Impact:** Não dá para filtrar por severidade nem enviar a um agregador de logs, e dados pessoais acabam em logs sem controle.
- **Recommendation:** Usar o módulo `logging` com `logger = logging.getLogger(__name__)` e níveis adequados, evitando registrar PII (ou mascarando-a).
- **Status:** ⚠️ Parcialmente corrigido — `print` foi substituído por `logging` (`app.py:16`, `logger` nos services), mas os e-mails continuam sendo logados em `services/usuario_service.py:35`, `:45` e `:48`.

### [LOW] L5 — Lista de categorias válidas hardcoded no controller
- **File:** `controllers.py`
- **Line/Snippet:** `controllers.py:52` — `categorias_validas = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]`
- **Description:** O domínio de categorias é definido como variável local dentro de `criar_produto`, e o default `"geral"` aparece de novo como literal em `controllers.py:41` e `:85`.
- **Impact:** A lista não pode ser reutilizada (e de fato não é, ver M3). Mudar as categorias exige editar o controller.
- **Recommendation:** Mover para o módulo de constantes junto com a categoria padrão.
- **Status:** ✅ Corrigido — `constants.py:3-4` (`CATEGORIAS_VALIDAS`, `CATEGORIA_PADRAO`).

## Total: 23 findings

---

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
