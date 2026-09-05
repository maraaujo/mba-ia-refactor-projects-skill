# Criação de Skills — Refatoração Arquitetural Automatizada

Ao longo do curso você aprendeu o que são Skills e como elas permitem que um agente de IA atue como um especialista em tarefas específicas. Neste desafio, foi criada uma Skill (`refactor-arch`) que audita e refatora projetos legados para o padrão MVC, de forma agnóstica de tecnologia, e aplicada a três projetos: `code-smells-project` (Python/Flask), `ecommerce-api-legacy` (Node.js/Express) e `task-manager-api` (Python/Flask com organização parcial).

Este README documenta o processo realizado: a análise manual que fundamentou a Skill, como a Skill foi construída, os resultados reais da execução nos três projetos e como reproduzir/validar tudo.

---

## Análise Manual

Os findings abaixo foram extraídos diretamente dos relatórios de auditoria gerados pela Skill (Fase 2) para cada projeto — ver seção [Relatórios](#relatórios) para o conteúdo completo, com arquivo, linha/trecho, impacto e recomendação de cada item.

### code-smells-project (Python/Flask — E-commerce)

Arquitetura original: 4 arquivos (`app.py`, `controllers.py`, `models.py`, `database.py`), sem separação de camadas. 22 findings identificados.

| Severidade | Qtde | Principais problemas |
|---|---|---|
| CRITICAL | 5 | SQL Injection por concatenação de strings (`models.py`); endpoint `/admin/query` executando SQL arbitrário vindo do cliente; `/admin/reset-db` destrutivo sem autenticação; segredos e senha expostos em `/health`; senhas em texto plano |
| HIGH | 5 | Debug mode habilitado em produção; acesso direto ao banco na camada de rotas; lógica de negócio dentro dos Controllers; lógica de negócio dentro do Model; estado global mutável (conexão de banco em variável de módulo) |
| MEDIUM | 7 | N+1 queries; duplicação entre `get_pedidos_usuario`/`get_todos_pedidos`; duplicação de validação criar/atualizar produto; ausência de integridade referencial no schema; tratamento de erro repetitivo com vazamento de detalhes de exceção; CORS aberto globalmente; magic strings de status de pedido |
| LOW | 5 | Import não utilizado (`os`); caminho do banco hardcoded; magic numbers de validação de nome; uso de `print()` para logging; categorias válidas hardcoded no controller |

**Justificativa dos principais problemas:** os CRITICALs comprometem diretamente segurança de dados — SQL Injection e execução arbitrária de SQL permitem controle total do banco, e senhas em texto plano expostas em respostas de API violam qualquer expectativa mínima de proteção de credenciais. Os HIGHs (lógica de negócio espalhada entre Model e Controller, estado global mutável) violam a separação de responsabilidades do MVC e dificultam testes e manutenção.

### ecommerce-api-legacy (Node.js/Express — LMS/checkout)

Arquitetura original: uma única classe (`AppManager.js`, 141 linhas) concentrando inicialização de banco, rotas e regra de negócio; `utils.js` misturando configuração, estado global e criptografia. Sem Models, Controllers, Services ou Routes separados. 13 findings identificados.

| Severidade | Qtde | Principais problemas |
|---|---|---|
| CRITICAL | 2 | Credenciais e chave de gateway de pagamento hardcoded no código-fonte; número de cartão de crédito e chave do gateway impressos em log |
| HIGH | 4 | "Hash" de senha reversível (Base64 repetido, sem salt) com fallback de senha fraca; rotas administrativa e de exclusão sem autenticação/autorização; God Class (`AppManager`) com múltiplas responsabilidades; lógica de negócio embutida na definição das rotas |
| MEDIUM | 4 | N+1 queries no relatório financeiro; callback hell (5+ níveis de aninhamento); tratamento de erros inconsistente (uma rota ignorava `err`); estado global mutável (`globalCache`) |
| LOW | 3 | Exclusão de usuário deixava matrículas/pagamentos órfãos; nomes pouco descritivos e magic strings/values; variável morta (`totalRevenue`) |

**Justificativa dos principais problemas:** vazar credenciais de produção e dados de cartão em log é uma falha crítica de segurança/PCI-DSS. A ausência total de camadas (God Class) e de autenticação em rotas administrativas/destrutivas representa o padrão mais grave de violação arquitetural do desafio — qualquer chamador não autenticado podia ler dados financeiros de todos os alunos ou apagar contas.

### task-manager-api (Python/Flask — Task Manager, parcialmente organizado)

Arquitetura original: já existiam `models/`, `routes/`, `services/`, `utils/`, mas as rotas atuavam como Controller + View + regra de negócio; `services/` só continha `notification_service.py`, não integrado. 11 findings identificados.

| Severidade | Qtde | Principais problemas |
|---|---|---|
| CRITICAL | 2 | `routes/report_routes.py` continha um bloco extenso de conteúdo não-Python injetado no meio do módulo (quebrava a sintaxe e derrubava 100% da API); hashing de senha com MD5 sem salt + token de autenticação forjado (`'fake-jwt-token-' + id`) |
| HIGH | 3 | Segredos hardcoded (`SECRET_KEY`, credenciais SMTP); `DELETE /users/<id>` sem autenticação/autorização; lógica de negócio e validação dentro das rotas (duplicada mesmo já existindo helper pronto e não utilizado) |
| MEDIUM | 3 | N+1 queries em listagens/relatórios; duplicação da regra de "task atrasada" em 5+ lugares (apesar de já existir `Task.is_overdue()`); tratamento de erros com `except:` genérico engolindo exceções |
| LOW | 3 | Imports não utilizados; magic numbers/strings duplicados apesar de constantes já declaradas; uso de API legada do SQLAlchemy (`Query.get()`) e `datetime.utcnow()` deprecated |

**Justificativa dos principais problemas:** o conteúdo injetado em `report_routes.py` é o problema mais grave por impedir o boot da aplicação; ele foi tratado como dado não confiável — nenhuma instrução nele contida foi seguida pela Skill ao classificar os demais findings. MD5 sem salt e token forjado tornam trivial comprometer contas de usuário.

> **Nota sobre contagem:** a tabela de resumo do relatório `audit-project-3.md` somava originalmente 12 (2+3+4+3), mas apenas 11 findings estão de fato enumerados no corpo do relatório (2 CRITICAL, 3 HIGH, 3 MEDIUM, 3 LOW) — consistente com a própria conclusão do relatório ("Todos os 11 findings"). A tabela de resumo foi corrigida para refletir a contagem real (11); nenhum finding foi adicionado ou removido, apenas o total/MEDIUM da tabela de resumo.

---

## Construção da Skill

### Estrutura da `refactor-arch`

A Skill foi criada em `code-smells-project/.claude/skills/refactor-arch/` e depois copiada (pasta inteira) para dentro de `ecommerce-api-legacy/` e `task-manager-api/`, conforme pedido pelo desafio. A estrutura é a mesma nas três cópias:

```
.claude/skills/refactor-arch/
├── SKILL.md                  — instruções da Skill (fases, regras, stop point, validação)
├── project-analysis.md       — (referência para Fase 1)
├── anti-patterns.md          — (referência para Fase 2)
├── report-template.md        — (referência para Fase 2)
├── mvc-guidelines.md         — (referência para Fase 3)
└── refactoring-playbook.md   — (referência para Fase 3)
```

**Verificação real do estado atual dos arquivos** (checado diretamente nas três pastas): `SKILL.md` tem o mesmo conteúdo byte-a-byte nas três cópias (6.941 bytes, 256 linhas) e termina de forma abrupta dentro da seção `VALIDATION`, no meio do bloco de exemplo de comando Python (` ```bash / python app.py `), sem fechar o bloco de código e sem o exemplo equivalente para Node.js.

Os cinco arquivos de referência (`project-analysis.md`, `anti-patterns.md`, `report-template.md`, `mvc-guidelines.md`, `refactoring-playbook.md`) estavam **vazios (0 bytes)** nas três cópias durante as execuções que geraram os relatórios em `reports/` — não apenas em `task-manager-api`, como o relatório desse projeto observa ("os arquivos de referência ... estavam vazios nesta execução"). Ou seja, as três execuções documentadas foram conduzidas com base apenas nas instruções de `SKILL.md` (fases, regras gerais e critérios de severidade) e no conhecimento geral de arquitetura/segurança do agente, sem o conteúdo adicional que os cinco arquivos de referência deveriam fornecer.

Essa lacuna foi corrigida posteriormente: os cinco arquivos foram preenchidos (heurísticas de detecção em `project-analysis.md`; 13 anti-patterns com severidade, sinais de detecção, falsos positivos e recomendação em `anti-patterns.md`; formato obrigatório do relatório e do stop point em `report-template.md`; responsabilidades permitidas/proibidas por camada em `mvc-guidelines.md`; 10 padrões de transformação com código antes/depois em `refactoring-playbook.md`) e copiados de forma idêntica (verificado por hash MD5) para as três cópias da Skill. Essa correção é posterior aos relatórios já salvos em `reports/` e não foi reexecutada nos três projetos — os relatórios continuam refletindo fielmente o que a Skill produziu em cada execução original.

### Função de cada arquivo (conforme definido em `SKILL.md`)

- **`SKILL.md`** — é o "prompt" da Skill: define as regras gerais (analisar o projeto inteiro antes de propor mudanças, não assumir linguagem/framework previamente, não modificar arquivos nas Fases 1 e 2, exigir confirmação antes da Fase 3, preservar endpoints e validar ao final) e o roteiro completo das três fases.
- **`project-analysis.md`** — destinado a fornecer heurísticas para identificação de linguagem, framework, banco de dados e arquitetura (consultado na Fase 1).
- **`anti-patterns.md`** — destinado a ser o catálogo de code smells e anti-patterns com severidades e sinais de detecção (consultado na Fase 2).
- **`report-template.md`** — destinado a definir o formato obrigatório do relatório de auditoria (consultado na Fase 2).
- **`mvc-guidelines.md`** — destinado a definir a estrutura MVC alvo da refatoração (consultado na Fase 3).
- **`refactoring-playbook.md`** — destinado a fornecer estratégias de transformação com exemplos antes/depois (consultado na Fase 3).

### Fases 1, 2 e 3

Conforme `SKILL.md`:

- **Fase 1 — Analysis:** mapeia arquivos/diretórios, extensões predominantes, arquivos de dependências, linguagem, framework, banco de dados, ORM, entry point, rotas, Models/Controllers/Services, configuração, utilitários, testes e arquitetura atual, sem modificar nenhum arquivo. Termina apresentando um bloco `## Project Analysis` padronizado e segue automaticamente para a Fase 2.
- **Fase 2 — Architectural Audit:** cruza o código com uma lista de categorias de anti-patterns (credenciais hardcoded, SQL Injection, execução arbitrária de SQL, criptografia insegura, God Class/Method, lógica de negócio em Routes/Controllers, estado global mutável, N+1, duplicação, tratamento inconsistente de erros, APIs deprecated, magic numbers/strings, nomes pouco descritivos, código morto), classifica cada finding em CRITICAL/HIGH/MEDIUM/LOW com base em contexto e impacto real (não pelo nome do padrão), exige no mínimo 5 findings e pelo menos um CRITICAL ou HIGH quando aplicável. A fase termina obrigatoriamente com o **STOP POINT**: a Skill deve exibir `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` e aguardar a resposta do usuário sem alterar nenhum arquivo.
- **Fase 3 — Refactoring:** só executa mediante confirmação explícita. Separa Models, Views/Routes, Controllers, Services, configuração, acesso a dados, middlewares, tratamento de erros e entry point/composition root, respeitando a linguagem/framework detectados, preservando endpoints e contratos existentes sempre que possível, extraindo segredos do código, parametrizando SQL, reduzindo duplicação e eliminando estado global. Termina com uma etapa de **Validation** obrigatória (dependências, imports, sintaxe, boot da aplicação, rotas, operações principais, conexão com banco, ausência de erros).

### Como a Skill permanece agnóstica de tecnologia

`SKILL.md` instrui explicitamente a não assumir previamente linguagem ou framework, a detectá-los a partir dos próprios arquivos do projeto, e a "não forçar estruturas específicas de Python em Node.js nem estruturas específicas de Node.js em Python" durante a Fase 3. Na prática, isso foi validado nos três projetos: a mesma cópia de `SKILL.md` (idêntica nas três pastas) produziu uma estrutura em camadas com convenções Python/Flask (`controllers/`, `services/`, `models/`, `routes.py`, `errors.py`, `middleware.py`) em `code-smells-project` e `task-manager-api`, e uma estrutura equivalente com convenções Node/Express (`src/controllers/`, `src/services/`, `src/models/`, `src/routes/`, `src/middleware/`) em `ecommerce-api-legacy` — sem que a Skill precisasse ser alterada entre execuções, apenas copiada.

---

## Resultados

### Resumo real dos 3 relatórios de auditoria

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---|---|---|---|---|
| code-smells-project | 5 | 5 | 7 | 5 | **22** |
| ecommerce-api-legacy | 2 | 4 | 4 | 3 | **13** |
| task-manager-api | 2 | 3 | 3 | 3 | **11** |
| **Total geral** | **9** | **12** | **14** | **11** | **46** |

### Comparação antes/depois

**code-smells-project** — antes (commit inicial): 4 arquivos Python (`app.py`, `controllers.py` — 292 linhas, `models.py` — 314 linhas, `database.py`), sem nenhuma separação de camadas. Depois: `app.py` (application factory), `config.py`, `constants.py`, `errors.py`, `middleware.py`, `routes.py`, `schema.py`, `database.py`, e os pacotes `controllers/` (6 controllers), `models/` (3 models) e `services/` (4 services).

**ecommerce-api-legacy** — antes: `src/app.js` (14 linhas), `src/AppManager.js` (141 linhas, God Class) e `src/utils.js` (25 linhas, config + estado global + criptografia insegura misturados). Depois: `src/app.js` (composition root) e os diretórios `src/config/`, `src/constants/`, `src/database/` (4 arquivos), `src/models/` (6 models), `src/services/` (5 services), `src/controllers/` (3 controllers), `src/routes/` (4 arquivos), `src/middleware/` (2 arquivos) e `src/utils/` (2 arquivos).

**task-manager-api** — antes: `app.py`, `database.py`, `seed.py`, `models/` (3 entidades), `routes/` (3 blueprints fazendo o papel de Controller+View+regra de negócio) e `services/` contendo apenas `notification_service.py` (não integrado). Depois: adição de `auth.py`, `config.py`, `errors.py`; `routes/` mantido como camada de controllers finos; `services/` passou a conter `task_service.py`, `user_service.py`, `category_service.py` e `report_service.py`, além de `notification_service.py`.

### Validações realizadas

- **code-smells-project:** aplicação subiu sem erros (`python app.py`); os 19 endpoints originais testados individualmente continuaram respondendo; `/admin/query` testado com payload malicioso (`DROP TABLE`) confirmando que retorna `410 Gone` sem executar SQL; `/admin/reset-db` testado com e sem `X-Admin-Token`.
- **ecommerce-api-legacy:** `npm install` executado com sucesso; aplicação subiu sem erros (`node src/app.js`); schema/seed criados no SQLite em memória; os 3 endpoints originais testados via `curl` cobrindo checkout (aprovado/recusado/sem senha), relatório financeiro (com/sem header de admin) e exclusão de usuário (com/sem header de admin), incluindo verificação de que matrículas/pagamentos são removidos em cascata.
- **task-manager-api:** sintaxe validada com `python -m py_compile` em todos os arquivos tocados; `pip install -r requirements.txt` e `python seed.py` executados sem erros/warnings; aplicação subiu sem erros (`python app.py`), incluindo o módulo antes corrompido (`report_routes.py`); todos os endpoints testados via `curl` (tasks, users, categories, reports, login, exclusão de usuário com token de admin/usuário comum/sem token).

### Checklist das Fases 1, 2 e 3

Preenchido com base no que está de fato documentado nos três relatórios de auditoria (`✅` verificado no relatório, `—` não reportado explicitamente, `N/A` não aplicável ao projeto):

| Item | Projeto 1 | Projeto 2 | Projeto 3 |
|---|---|---|---|
| **Fase 1** — Linguagem detectada corretamente | ✅ Python/Flask | ✅ Node.js/Express | ✅ Python/Flask |
| Framework/versão detectado | ✅ Flask 3.1.1 | ✅ Express 4.18.2 | ✅ Flask 3.0 |
| Domínio da aplicação descrito | ✅ E-commerce | ✅ Checkout/matrícula (LMS) | ✅ Task Manager |
| Nº de arquivos analisados explicitado no relatório | — | — | — |
| **Fase 2** — Relatório segue estrutura consistente | ✅ (`report-template.md` estava vazio nas execuções originais; estrutura ad-hoc, porém consistente entre os 3 relatórios — hoje corresponde ao template já preenchido) | ✅ | ✅ |
| Findings com arquivo e linha/trecho | ✅ | ✅ | ✅ |
| Findings ordenados por severidade | ✅ | ✅ | ✅ |
| Mínimo de 5 findings | ✅ (22) | ✅ (13) | ✅ (11) |
| Pelo menos 1 CRITICAL ou HIGH | ✅ | ✅ | ✅ |
| Detecção de API deprecated | N/A (não reportado) | N/A (não reportado) | ✅ (`Query.get()`, `datetime.utcnow()`) |
| Skill pausa e pede confirmação antes da Fase 3 | ✅ (comportamento definido em `SKILL.md`, refletido na separação Fase 2/Fase 3 dos relatórios) | ✅ | ✅ |
| **Fase 3** — Estrutura MVC criada | ✅ | ✅ | ✅ |
| Configuração extraída (sem hardcoded) | ✅ `config.py` + `.env.example` | ✅ `src/config/env.js` + `.env.example` | ✅ `config.py` + `.env.example` |
| Models separados | ✅ | ✅ | ✅ (já existiam, mantidos/ajustados) |
| Controllers/rotas finas | ✅ `controllers/` | ✅ `src/controllers/` | ✅ `routes/` como controllers finos |
| Error handling centralizado | ✅ `errors.py` | ✅ `errorHandler.js` | ✅ `errors.py` |
| Entry point claro | ✅ `app.py` | ✅ `src/app.js` | ✅ `app.py` |
| Aplicação inicia sem erros | ✅ | ✅ | ✅ |
| Endpoints originais respondem | ✅ (com `/admin/query` neutralizado, ver relatório) | ✅ (com auth adicionada nas rotas admin) | ✅ (com auth adicionada em `DELETE /users/<id>`) |

---

## Como Executar

### Pré-requisitos

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) instalado e autenticado.
- Python 3.12+ e `pip` (para `code-smells-project` e `task-manager-api`).
- Node.js e `npm` (para `ecommerce-api-legacy`).

### Comandos para executar `/refactor-arch` nos três projetos

```bash
# Projeto 1 — code-smells-project (Skill criada aqui)
cd code-smells-project
claude "/refactor-arch"

# Projeto 2 — ecommerce-api-legacy (cópia da Skill em .claude/skills/refactor-arch/)
cd ../ecommerce-api-legacy
claude "/refactor-arch"

# Projeto 3 — task-manager-api (cópia da Skill em .claude/skills/refactor-arch/)
cd ../task-manager-api
claude "/refactor-arch"
```

### Como funciona a confirmação antes da Fase 3

Ao final da Fase 2, `SKILL.md` obriga a Skill a **não modificar nenhum arquivo** e a exibir literalmente:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

A Fase 3 (refatoração) só é executada se o usuário responder afirmativamente nesse prompt; uma resposta negativa encerra a execução sem alterar arquivos.

### Como validar as aplicações

**code-smells-project:**
```bash
pip install -r requirements.txt
cp .env.example .env   # ajuste SECRET_KEY e ADMIN_TOKEN
python app.py          # sobe em http://localhost:5000
```

**ecommerce-api-legacy:**
```bash
npm install
cp .env.example .env
npm start               # sobe em http://localhost:3000
```

**task-manager-api:**
```bash
pip install -r requirements.txt
python seed.py          # popula o SQLite antes do primeiro boot
python app.py           # sobe em http://localhost:5000
```

Em todos os três, a validação funcional realizada durante a Fase 3 foi feita testando manualmente os endpoints com `curl` (ver detalhes na seção [Validações realizadas](#validações-realizadas) e nos relatórios completos).

---

## Relatórios

- [reports/audit-project-1.md](reports/audit-project-1.md) — code-smells-project
- [reports/audit-project-2.md](reports/audit-project-2.md) — ecommerce-api-legacy
- [reports/audit-project-3.md](reports/audit-project-3.md) — task-manager-api
