# Criação de Skills — Refatoração Arquitetural Automatizada

Este repositório traz a Skill `refactor-arch`, que analisa, audita e refatora projetos legados para o padrão MVC sem depender de uma tecnologia específica. Ela foi aplicada a três projetos:

- `code-smells-project` — Python/Flask, e-commerce;
- `ecommerce-api-legacy` — Node.js/Express, LMS com checkout;
- `task-manager-api` — Python/Flask, gerenciador de tarefas com organização parcial.

O README documenta a análise manual que fundamentou a Skill, como ela foi construída, os resultados nos três projetos e como reproduzir e validar tudo.

---

## Análise Manual

Os problemas abaixo foram identificados lendo o código original de cada projeto (commit `6d1ce62`, o boilerplate do desafio). Os relatórios em [`reports/`](#relatórios) trazem o arquivo, a linha exata, o impacto e a recomendação de cada um.

### code-smells-project (Python/Flask — E-commerce)

4 arquivos (`app.py`, `controllers.py`, `models.py`, `database.py`), com 780 linhas e nenhuma separação de camadas. Foram encontrados 23 problemas.

| Severidade | Qtde | Problemas |
|---|---|---|
| CRITICAL | 5 | SQL Injection por concatenação em toda a camada de dados (`models.py`); `POST /admin/query` executa SQL arbitrário vindo do cliente; `POST /admin/reset-db` apaga o banco sem autenticação; `SECRET_KEY` hardcoded e devolvida por `/health`; senhas em texto plano devolvidas pela API |
| HIGH | 6 | Debug ligado e servidor em `0.0.0.0`; SQL direto em rotas e controllers; regras de negócio nos controllers; regras de pedido e desconto na camada de dados; conexão SQLite global compartilhada entre threads; quantidade e tipos dos itens de pedido sem validação |
| MEDIUM | 7 | N+1 na listagem e na criação de pedidos; duplicação entre `get_pedidos_usuario` e `get_todos_pedidos`; validação de produto duplicada e divergente; schema sem chaves estrangeiras; `try/except` repetido devolvendo `str(e)`; CORS aberto; magic strings de status |
| LOW | 5 | Imports não usados; caminho do banco hardcoded; magic numbers (tamanho do nome, faixas de desconto); `print()` como logging, inclusive com e-mails; lista de categorias fixa no controller |

**Por que importam:** SQL Injection e o endpoint de SQL arbitrário dão controle total do banco a qualquer cliente. Senhas em texto plano e a `SECRET_KEY` exposta comprometem todas as contas e sessões. Os HIGHs quebram a separação MVC: como a regra de negócio está espalhada entre controller e model, nada pode ser testado isoladamente.

### ecommerce-api-legacy (Node.js/Express — LMS com checkout)

3 arquivos (`src/app.js`, `src/AppManager.js`, `src/utils.js`), com 180 linhas. Uma classe concentra banco, rotas e regras. Foram encontrados 13 problemas.

| Severidade | Qtde | Problemas |
|---|---|---|
| CRITICAL | 2 | Senha de banco e chave `pk_live_` de pagamento hardcoded; número do cartão e chave do gateway escritos em log |
| HIGH | 4 | "Hash" de senha reversível (Base64) com senha padrão `123456`; relatório financeiro e exclusão de usuário sem autenticação; God Class `AppManager`; checkout inteiro dentro do callback da rota |
| MEDIUM | 4 | N+1 no relatório financeiro (1 + C + 2·M queries); callback hell com 5 níveis; erros de banco ignorados; `globalCache` mutável compartilhado entre requisições |
| LOW | 3 | Exclusão de usuário deixa matrículas e pagamentos órfãos; variáveis de uma letra e magic strings (`"PAID"`, prefixo `"4"`); variável morta `totalRevenue` |

**Por que importam:** vazar cartão e chave de produção em log é falha de PCI-DSS. A God Class sem autenticação permite que qualquer cliente anônimo leia dados financeiros de todos os alunos e apague contas.

### task-manager-api (Python/Flask — Task Manager, parcialmente organizado)

15 arquivos Python, com 1.158 linhas, organizados em `models/`, `routes/`, `services/` e `utils/`. Mesmo assim, as rotas fazem o papel de controller, view e regra de negócio. Foram encontrados 12 problemas.

| Severidade | Qtde | Problemas |
|---|---|---|
| CRITICAL | 2 | `routes/report_routes.py` com conteúdo não-Python injetado que derrubava o boot (ver nota no relatório 3); senha com MD5 e token forjável `'fake-jwt-token-' + id` |
| HIGH | 4 | Debug fixo e servidor em `0.0.0.0`; `SECRET_KEY` e senha SMTP hardcoded; `DELETE /users/<id>` sem autenticação; validação e regras dentro das rotas, embora `utils/helpers.py` já tivesse esse código sem uso |
| MEDIUM | 3 | N+1 nas listagens e relatórios; regra de "task atrasada" copiada em 6 lugares em vez de `Task.is_overdue()`; `except:` sem tipo engolindo erros |
| LOW | 3 | Imports não usados; literais duplicados apesar de constantes declaradas; APIs deprecated (`Query.get()`, `datetime.utcnow()`) |

**Por que importam:** o token forjável e o MD5 tornam trivial assumir qualquer conta. Este projeto mostra que ter pastas com nomes de camadas não garante MVC: as rotas continuavam fazendo tudo.

---

## Construção da Skill

### Estrutura

A Skill foi criada em `code-smells-project/.claude/skills/refactor-arch/` e copiada inteira para `ecommerce-api-legacy/` e `task-manager-api/`. As três cópias são idênticas, o que foi verificado por hash MD5.

```
.claude/skills/refactor-arch/
├── SKILL.md                  — o prompt: regras gerais, 3 fases, stop point e validação
├── project-analysis.md       — Fase 1: heurísticas de linguagem, framework, banco e arquitetura
├── anti-patterns.md          — Fase 2: catálogo de 13 anti-patterns com severidade e sinais de detecção
├── report-template.md        — Fase 2: formato obrigatório do relatório e regras de preenchimento
├── mvc-guidelines.md         — Fase 3: responsabilidades permitidas e proibidas por camada
└── refactoring-playbook.md   — Fase 3: 10 transformações com código antes/depois
```

### Decisões de design

- **O `SKILL.md` é o roteiro e os arquivos de referência são o conhecimento.** O `SKILL.md` diz o que fazer em cada fase e qual arquivo consultar antes de cada uma. As heurísticas e os exemplos ficam nos arquivos de referência, o que mantém o prompt curto e permite melhorar o conhecimento sem mexer no fluxo.
- **As fases são sequenciais e têm uma trava.** As Fases 1 e 2 não podem modificar arquivos. A Fase 2 termina obrigatoriamente com `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`, e a Fase 3 só roda com um "sim" explícito.
- **Todo finding tem os mesmos campos, em todas as severidades.** São eles: `File`, `Line/Snippet`, `Description`, `Impact` e `Recommendation`. Antes do stop point, a Skill confere cada finding: se os campos estão preenchidos, se a linha citada existe e se a contagem do Summary bate. Um campo `Status` pode ser acrescentado depois da Fase 3, mas nunca substitui os cinco.
- **A severidade depende do contexto.** O catálogo traz uma "severidade sugerida" e também os falsos positivos. Exemplos: SQL parametrizado não é SQL Injection; um loop comum não é N+1; um valor de configuração não é credencial.

### Anti-patterns do catálogo e por quê

| # | Anti-pattern | Severidade sugerida | Por que entrou |
|---|---|---|---|
| 1 | Hardcoded Credentials | CRITICAL | Aparece nos 3 projetos (`SECRET_KEY`, `pk_live_`, senha SMTP) |
| 2 | SQL Injection | CRITICAL | Endêmico no `code-smells-project` |
| 3 | Arbitrary SQL Execution | CRITICAL | `POST /admin/query` executa qualquer SQL |
| 4 | God Class / God Method | CRITICAL/HIGH | `AppManager.js` e `models.py` concentram tudo |
| 5 | Business Logic in Routes/Controllers | HIGH | É o problema central dos 3 projetos, inclusive do parcialmente organizado |
| 6 | Global Mutable State | HIGH | Conexão SQLite global; `globalCache` |
| 7 | N+1 Queries | MEDIUM | Listagem de pedidos, relatório financeiro, listagem de tasks |
| 8 | Duplicated Code | MEDIUM | Validações e regra de "atrasada" copiadas |
| 9 | Inconsistent Error Handling | MEDIUM | `except:` sem tipo, `err` ignorado, `str(e)` devolvido ao cliente |
| 10 | Missing Input Validation | MEDIUM/HIGH | Quantidade de itens do pedido aceita valores negativos |
| 11 | Deprecated APIs | LOW/MEDIUM | `Query.get()`, `datetime.utcnow()`; o catálogo exige evidência de depreciação |
| 12 | Magic Numbers / Strings | LOW | Status, faixas de desconto, tamanhos mínimos |
| 13 | Poor Naming | LOW | `u`, `e`, `p`, `cc` no checkout |

A lista partiu da análise manual: cada anti-pattern corresponde a pelo menos um problema real dos três projetos. Os sinais de detecção são concretos (ex.: "query executada dentro de um loop sobre o resultado de outra query"), porque instruções vagas como "código ruim" não são acionáveis para o agente.

### Como a Skill é agnóstica de tecnologia

- O `project-analysis.md` detecta a stack pelos arquivos do projeto (`requirements.txt`, `package.json`, imports, chamadas como `app.listen`/`app.run`) e não presume a linguagem.
- O `mvc-guidelines.md` define as camadas pela responsabilidade, não por nomes de pasta de uma linguagem. O `SKILL.md` proíbe explicitamente impor estruturas de Python em Node.js e vice-versa.
- O `refactoring-playbook.md` alterna exemplos de Python/Flask e Node.js/Express (ex.: segredo em variável de ambiente, God Class em camadas, tratamento de erro central). A conversão de callbacks para `async/await` só se aplica quando a linguagem tem esse recurso.
- Resultado: a mesma Skill, sem alterações, gerou `controllers/`, `services/`, `models/`, `routes.py`, `errors.py` nos projetos Flask e `src/controllers/`, `src/services/`, `src/models/`, `src/routes/`, `src/middleware/` no projeto Express.

### Desafios encontrados e como foram resolvidos

1. **Arquivos de referência vazios nas primeiras execuções.** Os relatórios originais foram gerados só com o `SKILL.md`. Os cinco arquivos foram então preenchidos. O relatório 1 foi refeito com a Skill completa, e os relatórios 2 e 3 foram reconferidos linha a linha contra o snapshot original.
2. **Findings sem detalhe nas severidades menores.** O professor apontou que, no relatório 1, os findings HIGH, MEDIUM e LOW tinham só o status. A Fase 2 ganhou a seção "Campos obrigatórios em TODAS as severidades", com uma verificação finding a finding antes do stop point. O `report-template.md` passou a dizer que a regra vale para todas as severidades, e os três relatórios foram refeitos nesse formato.
3. **Linhas imprecisas.** Várias referências estavam deslocadas (ex.: `AppManager.js:49` em vez de `:45`) ou eram aproximadas (`~319`). Todas foram reconferidas no código original.
4. **Conteúdo injetado no código.** No `task-manager-api`, um bloco de texto colado em `routes/report_routes.py` tinha instruções dirigidas à Skill. Ele foi tratado como dado não confiável, e o `SKILL.md` e o template orientam a registrar esse tipo de situação em `## Notes`, sem seguir as instruções.
5. **Preservar contratos sem manter falhas.** Remover `POST /admin/query` quebraria o requisito de manter os endpoints originais. A rota foi mantida, mas inerte: sempre responde `410 Gone` e não executa SQL.
6. **Resíduos que só aparecem rodando a aplicação.** O servidor real do `task-manager-api` ainda subia com `debug=True` e porta fixa, e o reloader travava o SQLite no Windows. Isso foi corrigido e registrado no relatório 3. Para que a validação seja repetível, foi criado `scripts/smoke_test.py`.

---

## Resultados

### Resumo dos relatórios de auditoria

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---|---|---|---|---|
| code-smells-project | 5 | 6 | 7 | 5 | **23** |
| ecommerce-api-legacy | 2 | 4 | 4 | 3 | **13** |
| task-manager-api | 2 | 4 | 3 | 3 | **12** |
| **Total geral** | **9** | **14** | **14** | **11** | **48** |

### Estrutura antes e depois

**code-smells-project**

```
Antes                          Depois
app.py                         app.py               (application factory / composition root)
controllers.py                 config.py            (configuração via ambiente)
models.py                      constants.py
database.py                    routes.py            (camada de rotas)
                               controllers/         (6 controllers finos)
                               services/            (5 services com a regra de negócio)
                               models/              (3 models com SQL parametrizado)
                               database.py, schema.py
                               errors.py            (tratamento de erro central)
                               middleware.py        (admin_required)
```

**ecommerce-api-legacy**

```
Antes                          Depois
src/app.js                     src/app.js           (composition root)
src/AppManager.js              src/config/env.js
src/utils.js                   src/constants/paymentStatus.js
                               src/database/        (Database, connection, schema, seed)
                               src/routes/          (4 arquivos)
                               src/controllers/     (3 controllers)
                               src/services/        (5 services)
                               src/models/          (6 models)
                               src/middleware/      (adminAuth, errorHandler)
                               src/utils/           (AppError, asyncHandler)
```

**task-manager-api**

```
Antes                                   Depois
app.py                                  app.py               (create_app, debug e porta via config)
database.py                             config.py, errors.py, auth.py
models/  (task, user, category)         models/              (hash seguro, utc_now, is_overdue)
routes/  (controller+view+regra)        routes/              (controllers finos)
services/notification_service.py        services/            (task, user, category, report, notification)
utils/helpers.py (não usado)            utils/helpers.py     (constantes e validações centralizadas)
seed.py                                 seed.py
```

### Aplicações rodando após a refatoração

O script [`scripts/smoke_test.py`](scripts/smoke_test.py) sobe cada aplicação como um servidor real, com `python app.py` ou `node src/app.js` e banco temporário. Em seguida, ele chama todos os endpoints originais e os principais casos de erro e de segurança. Os logs completos, com a saída de cada servidor, estão em [`docs/validation/`](docs/validation/).

| Projeto | Comando de boot | Testes HTTP | Resultado |
|---|---|---|---|
| code-smells-project | `python app.py` | 24 (19 endpoints originais + `/` + casos de segurança) | ✅ 24/24 |
| ecommerce-api-legacy | `node src/app.js` | 7 (3 endpoints em todos os cenários) | ✅ 7/7 |
| task-manager-api | `python seed.py && python app.py` | 26 (22 endpoints originais + casos de erro e autorização) | ✅ 26/26 |

Trecho de [`docs/validation/ecommerce-api-legacy.log`](docs/validation/ecommerce-api-legacy.log):

```
$ node src/app.js
servidor ouvindo em http://127.0.0.1:5102
PASS 200 (esperado 200) POST /api/checkout — checkout aprovado
PASS 400 (esperado 400) POST /api/checkout — checkout recusado
PASS 400 (esperado 400) POST /api/checkout — checkout usuário novo sem senha
PASS 401 (esperado 401) GET /api/admin/financial-report — relatório financeiro sem chave
PASS 200 (esperado 200) GET /api/admin/financial-report — relatório financeiro com chave
PASS 401 (esperado 401) DELETE /api/users/1 — deletar usuário sem chave
PASS 200 (esperado 200) DELETE /api/users/1 — deletar usuário com chave
RESULTADO: 7 passaram, 0 falharam
```

Trecho de [`docs/validation/code-smells-project.log`](docs/validation/code-smells-project.log):

```
PASS 401 (esperado 401) POST /login — login com SQL injection
PASS 400 (esperado 400) POST /pedidos — criar pedido com quantidade negativa
PASS 410 (esperado 410) POST /admin/query — /admin/query neutralizado
PASS 200 (esperado 200) GET /produtos/1 — tabela produtos intacta após DROP
PASS 403 (esperado 403) POST /admin/reset-db — reset-db sem token
PASS 200 (esperado 200) POST /admin/reset-db — reset-db com token
RESULTADO: 24 passaram, 0 falharam
```

### Checklist de validação

| Item | Projeto 1 | Projeto 2 | Projeto 3 |
|---|---|---|---|
| **Fase 1** — Linguagem detectada corretamente | ✅ Python | ✅ JavaScript (Node.js) | ✅ Python |
| Framework detectado corretamente | ✅ Flask 3.1.1 | ✅ Express 4.18.2 | ✅ Flask 3.0 + SQLAlchemy |
| Domínio da aplicação descrito corretamente | ✅ E-commerce | ✅ LMS com checkout | ✅ Task Manager |
| Número de arquivos analisados condiz com a realidade | ✅ 4 arquivos, 780 linhas | ✅ 3 arquivos, 180 linhas | ✅ 15 arquivos, 1.158 linhas |
| **Fase 2** — Relatório segue o template | ✅ | ✅ | ✅ |
| Cada finding tem arquivo e linhas exatos | ✅ | ✅ | ✅ (exceto o CRITICAL de conteúdo injetado, ver relatório) |
| Findings ordenados por severidade | ✅ | ✅ | ✅ |
| Mínimo de 5 findings | ✅ 23 | ✅ 13 | ✅ 12 |
| Pelo menos 1 CRITICAL ou HIGH | ✅ 5 + 6 | ✅ 2 + 4 | ✅ 2 + 4 |
| Detecção de APIs deprecated | N/A (nenhuma no código) | N/A (nenhuma no código) | ✅ `Query.get()`, `datetime.utcnow()` |
| Skill pausa e pede confirmação antes da Fase 3 | ✅ | ✅ | ✅ |
| **Fase 3** — Estrutura segue o padrão MVC | ✅ | ✅ | ✅ |
| Configuração extraída para módulo de config | ✅ `config.py` + `.env.example` | ✅ `src/config/env.js` + `.env.example` | ✅ `config.py` + `.env.example` |
| Models abstraem os dados | ✅ `models/` | ✅ `src/models/` | ✅ `models/` |
| Views/Routes separadas | ✅ `routes.py` | ✅ `src/routes/` | ✅ `routes/` |
| Controllers concentram o fluxo | ✅ `controllers/` + `services/` | ✅ `src/controllers/` + `src/services/` | ✅ `routes/` finos + `services/` |
| Error handling centralizado | ✅ `errors.py` | ✅ `src/middleware/errorHandler.js` | ✅ `errors.py` |
| Entry point claro | ✅ `app.py` | ✅ `src/app.js` | ✅ `app.py` |
| Aplicação inicia sem erros | ✅ | ✅ | ✅ |
| Endpoints originais respondem | ✅ 19/19 | ✅ 3/3 | ✅ 22/22 |

### Comportamento da Skill em stacks diferentes

- **Monolito Python (`code-smells-project`):** foi o caso com mais findings (23), porque não havia nenhuma camada. A Fase 3 criou todas as camadas do zero. O ponto delicado foi preservar os 19 endpoints, inclusive o `/admin/query`, mantido apenas como rota inerte.
- **Node.js/Express (`ecommerce-api-legacy`):** a Skill reconheceu os problemas próprios da stack, como callback hell e erros de callback ignorados, e aplicou transformações de JavaScript (promisificação, `async/await`, middleware de erro do Express) em vez de copiar a estrutura Python. Os nomes de campo do JSON (`usr`, `eml`, `c_id`) foram mantidos para não quebrar o contrato.
- **Python parcialmente organizado (`task-manager-api`):** a Skill não se deixou enganar pelas pastas `models/`, `routes/` e `services/`. Ela identificou que as rotas faziam o papel das três camadas, que o helper e o `is_overdue()` existiam sem uso, e propôs mudanças incrementais (services e controllers finos) em vez de reescrever a estrutura que já servia.
- **Mudanças de contrato:** em todos os casos, as únicas mudanças são correções de segurança deliberadas e documentadas nos relatórios. São elas: a autenticação nas rotas administrativas e de exclusão; a retirada de `password` e `secret_key` das respostas; e o `410` do `/admin/query`.

---

## Como Executar

### Pré-requisitos

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) instalado e autenticado.
- Python 3.12+ e `pip`, para `code-smells-project` e `task-manager-api`.
- Node.js 18+ e `npm`, para `ecommerce-api-legacy`.

### Executar a Skill

```bash
# Projeto 1 — code-smells-project (Skill criada aqui)
cd code-smells-project
claude "/refactor-arch"

# Projeto 2 — ecommerce-api-legacy (cópia da Skill)
cd ../ecommerce-api-legacy
claude "/refactor-arch"

# Projeto 3 — task-manager-api (cópia da Skill)
cd ../task-manager-api
claude "/refactor-arch"
```

As Fases 1 e 2 rodam em sequência e só leem os arquivos. Ao final da Fase 2, a Skill mostra o relatório e para em:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

A Fase 3 só executa com `y`. Uma resposta `n` encerra a execução sem alterar nenhum arquivo.

### Validar a refatoração

Instale as dependências dos três projetos:

```bash
pip install -r code-smells-project/requirements.txt -r task-manager-api/requirements.txt
```

```bash
npm install --prefix ecommerce-api-legacy
```

Na raiz do repositório, rode o smoke test. Ele sobe os três servidores, testa todos os endpoints e grava os logs em `docs/validation/`:

```bash
python scripts/smoke_test.py
```

Para subir cada aplicação manualmente:

```bash
cd code-smells-project && cp .env.example .env && python app.py
```

```bash
cd ecommerce-api-legacy && cp .env.example .env && npm start
```

```bash
cd task-manager-api && cp .env.example .env && python seed.py && python app.py
```

---

## Relatórios

- [reports/audit-project-1.md](reports/audit-project-1.md) — code-smells-project
- [reports/audit-project-2.md](reports/audit-project-2.md) — ecommerce-api-legacy
- [reports/audit-project-3.md](reports/audit-project-3.md) — task-manager-api
