# Architectural Audit Report — ecommerce-api-legacy

## Project Analysis

- **Language:** JavaScript (Node.js)
- **Framework:** Express 4.18.2
- **Database:** SQLite em memória (`:memory:`) via `sqlite3` 5.1.6
- **ORM / Database Library:** Nenhum ORM — driver `sqlite3` direto, com SQL parametrizado
- **Application Type:** API REST de checkout e matrícula em cursos (mistura de e-commerce e LMS) — 3 endpoints
- **Entry Point:** `src/app.js`
- **Current Architecture:** Sem camadas. A classe `AppManager` (`src/AppManager.js`) cria e popula o schema, registra todas as rotas e contém toda a regra de negócio. `src/utils.js` mistura configuração, estado global e "criptografia". Não há Models, Controllers, Services nem Routes separados.
- **Main Directories:** `src/` com 3 arquivos (`app.js`, `AppManager.js`, `utils.js`)
- **Source Files Analyzed:** 3 arquivos JavaScript, 180 linhas (`src/app.js` 14, `src/AppManager.js` 141, `src/utils.js` 25)
- **Main Architectural Problems:** God Class (`AppManager`); regra de negócio dentro dos callbacks de rota; credenciais e chave de pagamento hardcoded; rotas administrativas e destrutivas sem autenticação; estado global mutável; callback hell e N+1 no relatório financeiro.

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 2 |
| HIGH | 4 |
| MEDIUM | 4 |
| LOW | 3 |
| **Total** | **13** |

## Notes

> Observações sobre o processo de auditoria — não são findings de código.

- **Código auditado:** snapshot original do projeto no commit `6d1ce62`. Todos os arquivos e linhas citados em `File` / `Line/Snippet` referem-se a esse snapshot. `src/AppManager.js` e `src/utils.js` não existem mais na árvore atual, porque foram substituídos na Fase 3.
- **Revisão de formato (2026-10-27):** o relatório foi reescrito no formato de `report-template.md`, com os 5 campos obrigatórios separados em todos os findings. As linhas foram reconferidas no snapshot. A versão anterior tinha várias referências deslocadas, como o log do cartão citado em `AppManager.js:49` (correto: `:45`), as rotas administrativas em `:87`/`:139` (corretos: `:80`/`:131`) e a classe em `:7-150` (correto: `:4-139`). O conteúdo dos 13 findings não mudou.
- **Campo `Status`:** cada finding traz um campo extra `Status` com o resultado da Fase 3, conferido na árvore atual. Esse campo não substitui nenhum dos cinco campos obrigatórios.
- **Histórico:**
  - **2026-09-05** — Fase 3 aplicada. `AppManager.js` e `utils.js` foram substituídos pela estrutura `src/{config,constants,database,models,services,controllers,routes,middleware,utils}`, e `src/app.js` virou o composition root. Foram adicionados `.env.example`, `.gitignore`, as dependências `bcryptjs` e `dotenv` e o arquivo `api.http`.
  - **Validação (2026-09-05):** `npm install` e `node src/app.js` rodaram sem erros de boot, e o schema e o seed foram criados. Os 3 endpoints originais foram testados com `curl`:
    - checkout aprovado (`200`), recusado (`400`) e usuário novo sem senha (`400`);
    - relatório financeiro sem `x-admin-key` (`401`) e com a chave (`200`, query única);
    - exclusão de usuário sem chave (`401`) e com chave (`200`);
    - relatório após a exclusão, sem as matrículas e os pagamentos do usuário removido (exclusão em cascata).

    A única mudança de contrato é intencional: o header `x-admin-key` passou a ser exigido nas duas rotas administrativas.
  - **Validação (2026-10-28):** `scripts/smoke_test.py` sobe o servidor real (`node src/app.js`). Os 7 testes HTTP passaram, cobrindo os 3 endpoints com os casos de sucesso, recusa, senha ausente e autorização. O log está em `docs/validation/ecommerce-api-legacy.log`.

## Findings

### [CRITICAL] Credenciais e chave de pagamento hardcoded
- **File:** `src/utils.js`
- **Line/Snippet:** `src/utils.js:1-7` — `dbPass: "senha_super_secreta_prod_123"` (linha 3), `paymentGatewayKey: "pk_live_1234567890abcdef"` (linha 4)
- **Description:** O objeto `config` contém usuário e senha de banco e uma chave de gateway de pagamento com prefixo de produção (`pk_live_`), versionados no repositório.
- **Impact:** Qualquer pessoa com acesso ao repositório obtém credenciais de produção, o que permite comprometer o gateway de pagamento e o banco.
- **Recommendation:** Ler os valores de variáveis de ambiente, manter `.env` fora do versionamento e rotacionar as chaves já expostas.
- **Status:** ✅ Corrigido — `src/config/env.js:4-7` lê `PORT`, `DATABASE_URL`, `PAYMENT_GATEWAY_KEY` e `ADMIN_API_KEY` do ambiente, e há `.env.example`. As configurações não usadas (`dbUser`, `dbPass`, `smtpUser`) foram removidas.

### [CRITICAL] Número de cartão e chave do gateway escritos em log
- **File:** `src/AppManager.js`
- **Line/Snippet:** `src/AppManager.js:45` — ``console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`)``
- **Description:** A cada checkout, o número completo do cartão e a chave do gateway vão para o stdout da aplicação.
- **Impact:** Violação de PCI-DSS. Dados de cartão e segredos ficam expostos em qualquer destino de log (arquivo, agregador, console de deploy).
- **Recommendation:** Nunca registrar PAN ou segredos. Se o log for necessário, mascarar o cartão (ex.: últimos 4 dígitos).
- **Status:** ✅ Corrigido — `src/services/paymentGatewayService.js` decide o status sem logar dados sensíveis. O único `console.log` restante é a mensagem de boot em `src/app.js:23`.

### [HIGH] "Hash" de senha reversível e senha padrão fraca
- **File:** `src/utils.js`, `src/AppManager.js`
- **Line/Snippet:** `src/utils.js:17-23` (`badCrypto`: Base64 repetido e truncado em 10 caracteres); `src/AppManager.js:68` — `let hash = badCrypto(p || "123456");`
- **Description:** A função usada como hash é só uma codificação Base64 dos dois primeiros caracteres, sem salt. Se o cliente não envia senha, o usuário é criado com a senha `"123456"`.
- **Impact:** Senhas recuperáveis ou colidíveis trivialmente, e contas criadas no checkout ficam acessíveis com uma senha conhecida.
- **Recommendation:** Usar `bcrypt`/`argon2` com salt e tornar a senha obrigatória ao criar usuário.
- **Status:** ✅ Corrigido — `src/services/passwordService.js:1-10` usa `bcryptjs`. `src/services/checkoutService.js:21` responde `400` quando um usuário novo não envia senha.

### [HIGH] Rotas administrativa e destrutiva sem autenticação
- **File:** `src/AppManager.js`
- **Line/Snippet:** `src/AppManager.js:80` — `app.get('/api/admin/financial-report', ...)`; `src/AppManager.js:131` — `app.delete('/api/users/:id', ...)`
- **Description:** O relatório financeiro de todos os alunos e a exclusão de usuários não verificam identidade nem permissão.
- **Impact:** Qualquer cliente anônimo lê dados financeiros e nomes de alunos e apaga contas.
- **Recommendation:** Aplicar um middleware de autenticação/autorização administrativa nessas rotas, com o segredo vindo da configuração.
- **Status:** ✅ Corrigido — `src/middleware/adminAuth.js:4-12` exige o header `x-admin-key` igual a `ADMIN_API_KEY` e é aplicado em `src/routes/reportRoutes.js:7` e `src/routes/userRoutes.js:7`.

### [HIGH] God Class com múltiplas responsabilidades
- **File:** `src/AppManager.js`
- **Line/Snippet:** `src/AppManager.js:4-139` — classe `AppManager`. Contém `initDb()` (schema + seed, linhas 10-23) e `setupRoutes()` (rotas + regra de negócio, linhas 25-138).
- **Description:** Uma única classe cria e popula o banco, registra todas as rotas HTTP e implementa checkout, pagamento, matrícula, auditoria, relatório e exclusão.
- **Impact:** Alto acoplamento. Nenhuma parte pode ser testada isoladamente, e qualquer alteração arrisca quebrar fluxos não relacionados.
- **Recommendation:** Separar em módulo de banco (conexão, schema, seed), Models, Services, Controllers e Routes.
- **Status:** ✅ Corrigido — `AppManager.js` foi removido. As responsabilidades estão em `src/database/`, `src/models/`, `src/services/`, `src/controllers/` e `src/routes/`.

### [HIGH] Regra de negócio dentro do callback da rota de checkout
- **File:** `src/AppManager.js`
- **Line/Snippet:** `src/AppManager.js:28-78` — `app.post('/api/checkout', ...)`. Inclui a decisão de pagamento (linhas 45-48), a criação de usuário (66-72), a matrícula (50), o pagamento (54) e a auditoria (57).
- **Description:** A orquestração inteira do checkout está no handler HTTP: validação, busca de curso, criação de usuário, decisão de aprovação, gravação de matrícula, pagamento e log de auditoria.
- **Impact:** A regra não pode ser reutilizada nem testada sem o Express, e erros de negócio e de HTTP ficam misturados.
- **Recommendation:** Extrair para um `checkoutService`. A rota/controller só lê o request e traduz o resultado em resposta HTTP.
- **Status:** ✅ Corrigido — `src/services/checkoutService.js:11` (`checkout`) é chamado pelo controller fino `src/controllers/checkoutController.js:4`.

### [MEDIUM] N+1 queries no relatório financeiro
- **File:** `src/AppManager.js`
- **Line/Snippet:** `src/AppManager.js:89-127` — para cada curso, `SELECT * FROM enrollments WHERE course_id = ?` (linha 92); para cada matrícula, `SELECT name, email FROM users` (linha 104) e `SELECT amount, status FROM payments` (linha 106)
- **Description:** O número de queries é 1 + C + 2·M (C cursos, M matrículas), todas disparadas dentro de `forEach`.
- **Impact:** A latência cresce linearmente com a base, e a contagem manual de callbacks pendentes torna o código frágil.
- **Recommendation:** Uma única query com `LEFT JOIN` entre cursos, matrículas, usuários e pagamentos, agregada na aplicação.
- **Status:** ✅ Corrigido — `src/models/reportModel.js:1-13` faz uma única query com `LEFT JOIN`, e a agregação fica em `src/services/reportService.js:4`.

### [MEDIUM] Callback hell no fluxo de checkout
- **File:** `src/AppManager.js`
- **Line/Snippet:** `src/AppManager.js:37-77` — `db.get` (curso) → `db.get` (usuário) → `db.run` (matrícula) → `db.run` (pagamento) → `db.run` (auditoria), 5 níveis aninhados, alternando `this` e `self` (linhas 50, 54, 57)
- **Description:** O fluxo é escrito com callbacks aninhados, e cada nível trata ou ignora o erro de um jeito.
- **Impact:** Leitura difícil, propagação de erro inconsistente e risco de bugs de contexto (`this` vs `self`) em manutenção.
- **Recommendation:** Promisificar o acesso ao banco e reescrever o fluxo com `async/await`.
- **Status:** ✅ Corrigido — `src/database/Database.js` promisifica `run`/`get`/`all`, e o checkout é `async` (`src/services/checkoutService.js:11`).

### [MEDIUM] Tratamento de erros inconsistente e erros ignorados
- **File:** `src/AppManager.js`
- **Line/Snippet:** `src/AppManager.js:133-135` — o callback `(err) => { res.send(...) }` de `DELETE /api/users/:id` ignora `err`; também ignoram `err` as linhas 57 (auditoria), 92 (matrículas), 104 e 106 (usuário e pagamento no relatório)
- **Description:** Algumas operações checam `err` e respondem 4xx/5xx; outras descartam o erro e seguem como se tivessem sucesso.
- **Impact:** Falhas silenciosas, como responder sucesso quando a exclusão falhou ou quebrar com `enrollments.length` de `undefined` no relatório.
- **Recommendation:** Propagar erros de forma uniforme até um middleware central de erro do Express.
- **Status:** ✅ Corrigido — `src/middleware/errorHandler.js` está registrado em `src/app.js:20`, com `AppError` (`src/utils/AppError.js`) e `asyncHandler` (`src/utils/asyncHandler.js`) nos controllers.

### [MEDIUM] Estado global mutável compartilhado entre requisições
- **File:** `src/utils.js`, `src/AppManager.js`
- **Line/Snippet:** `src/utils.js:9` — `let globalCache = {};`; `src/utils.js:12-15` (`logAndCache` mutando o objeto); uso em `src/AppManager.js:59`
- **Description:** Um objeto de módulo é escrito a cada checkout e compartilhado por todas as requisições concorrentes, sem limite de tamanho nem leitura em lugar nenhum.
- **Impact:** Acoplamento oculto entre requisições e crescimento de memória sem limite.
- **Recommendation:** Remover o cache ou, se necessário, substituí-lo por um cache explícito e injetado.
- **Status:** ✅ Corrigido — `globalCache` e `logAndCache` foram removidos e não há estado de módulo mutável em `src/`.

### [LOW] Exclusão de usuário deixa matrículas e pagamentos órfãos
- **File:** `src/AppManager.js`
- **Line/Snippet:** `src/AppManager.js:131-137` — `DELETE FROM users WHERE id = ?` (linha 133); a própria resposta admite: `"Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco."` (linha 135)
- **Description:** A exclusão remove só a linha de `users`, sem tratar `enrollments` e `payments` relacionados, e o schema não declara chaves estrangeiras (linhas 12-16).
- **Impact:** Registros órfãos, e o relatório financeiro passa a mostrar alunos `Unknown` com receita de usuários inexistentes.
- **Recommendation:** Remover pagamentos e matrículas do usuário antes dele, no serviço de usuário.
- **Status:** ✅ Corrigido — `src/services/userService.js:5` remove pagamentos (`src/models/paymentModel.js:9-10`), matrículas (`src/models/enrollmentModel.js:13-14`) e depois o usuário (`src/models/userModel.js:13-14`).

### [LOW] Nomes pouco descritivos e magic strings
- **File:** `src/AppManager.js`
- **Line/Snippet:** `src/AppManager.js:29-33` — `let u`, `e`, `p`, `cid`, `cc`; `src/AppManager.js:46` — `cc.startsWith("4") ? "PAID" : "DENIED"`; `src/AppManager.js:108` — `payment.status === 'PAID'`
- **Description:** Variáveis de uma letra e literais de status e de regra de cartão repetidos sem constante nomeada.
- **Impact:** Leitura difícil, e alterar um status exige caçar literais, com risco de divergência.
- **Recommendation:** Renomear as variáveis e extrair constantes de status de pagamento.
- **Status:** ✅ Corrigido — `src/constants/paymentStatus.js:1-6` (`PAYMENT_STATUS`), usado em services e no seed, com nomes internos descritivos (`username`, `email`, `cardNumber`...). Os nomes dos campos JSON da API (`usr`, `eml`, `pwd`, `c_id`, `card`) foram mantidos para preservar o contrato.

### [LOW] Código morto — `totalRevenue`
- **File:** `src/utils.js`, `src/AppManager.js`
- **Line/Snippet:** `src/utils.js:10` — `let totalRevenue = 0;`, exportado em `src/utils.js:25`; importado em `src/AppManager.js:2` e nunca usado
- **Description:** Variável declarada, exportada e importada, mas nunca lida nem atualizada.
- **Impact:** Ruído, e sugere um acumulador de receita que não existe.
- **Recommendation:** Remover.
- **Status:** ✅ Corrigido — removida junto com `src/utils.js`.

## Total: 13 findings

---

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
