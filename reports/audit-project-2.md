# Relatório de Auditoria e Refatoração Arquitetural

**Projeto:** `ecommerce-api-legacy`
**Skill:** `refactor-arch`
**Data:** 2026-09-05

---

## Fase 1 — Análise do Projeto

- **Language:** JavaScript (Node.js)
- **Framework:** Express 4.18.2
- **Database:** SQLite (`sqlite3` v5.1.6, banco em memória — `:memory:`)
- **ORM / Database Library:** Nenhum ORM — acesso via driver `sqlite3` cru, com SQL parametrizado
- **Application Type:** API REST (checkout/matrícula em cursos — mistura de e-commerce e LMS)
- **Entry Point:** `src/app.js`
- **Arquitetura original:** Sem camadas — uma única classe (`AppManager`) concentrava inicialização de banco, definição de rotas e regra de negócio. `utils.js` misturava configuração, estado global e criptografia. Não havia Models, Controllers, Services ou Routes separados.
- **Diretórios principais (antes):** `src/` com apenas 3 arquivos (`app.js`, `AppManager.js`, `utils.js`)
- **Principais problemas arquiteturais identificados:**
  - God Class (`AppManager`) com múltiplas responsabilidades
  - Lógica de negócio embutida diretamente nas rotas
  - Credenciais e chaves sensíveis hardcoded
  - Ausência de autenticação/autorização em rotas administrativas e destrutivas
  - Estado global mutável (`globalCache`, `totalRevenue`)
  - Callback hell e N+1 queries no relatório financeiro

---

## Fase 2 — Findings da Auditoria

### Resumo de Severidade

| Severidade | Qtde |
|---|---|
| CRITICAL | 2 |
| HIGH | 4 |
| MEDIUM | 4 |
| LOW | 3 |

### Findings Detalhados

**1. [CRITICAL] Credenciais e chaves sensíveis hardcoded**
- **Arquivo/trecho:** `src/utils.js:3-9` — `dbPass: "senha_super_secreta_prod_123"`, `paymentGatewayKey: "pk_live_1234567890abcdef"`
- **Descrição:** Objeto `config` com usuário/senha de banco e chave de gateway de pagamento (aparentando ser chave de produção) hardcoded no código-fonte e versionado no repositório.
- **Impacto:** Vazamento de credenciais de produção para qualquer pessoa com acesso ao repositório; comprometimento do gateway de pagamento e do banco.
- **Recomendação:** Extrair para variáveis de ambiente, nunca commitar segredos, adicionar `.env` ao `.gitignore`, rotacionar as chaves já expostas.

**2. [CRITICAL] Exposição de dados sensíveis em log**
- **Arquivo/trecho:** `src/AppManager.js:49` — `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)`
- **Descrição:** Número completo do cartão de crédito e a chave do gateway de pagamento eram impressos em log de aplicação.
- **Impacto:** Violação de PCI-DSS, vazamento de dados de cartão via logs (arquivo, stdout, agregadores de log).
- **Recomendação:** Nunca logar PAN/segredos; mascarar dados sensíveis se o log for necessário.

**3. [HIGH] Criptografia de senha insegura e reversível**
- **Arquivo/trecho:** `src/utils.js:20-26` (`badCrypto`), uso em `src/AppManager.js:75`
- **Descrição:** "Hash" de senha era apenas Base64 repetido 10.000 vezes e truncado — reversível e sem salt. Se a senha não fosse enviada, usava fallback inseguro `"123456"`.
- **Impacto:** Senhas de usuários recuperáveis trivialmente; contas comprometidas em caso de vazamento do banco.
- **Recomendação:** Usar `bcrypt`/`argon2` com salt por usuário; exigir senha obrigatória no cadastro.

**4. [HIGH] Ausência de autenticação/autorização em rotas sensíveis**
- **Arquivo/trecho:** `src/AppManager.js:87` (`GET /api/admin/financial-report`) e `src/AppManager.js:139` (`DELETE /api/users/:id`)
- **Descrição:** Rota administrativa de relatório financeiro e rota de exclusão de usuário não possuíam nenhuma verificação de autenticação/autorização.
- **Impacto:** Qualquer chamador não autenticado podia ler dados financeiros de todos os alunos ou apagar contas de usuário.
- **Recomendação:** Adicionar middleware de autenticação e checagem de permissão antes de processar essas rotas.

**5. [HIGH] God Class com múltiplas responsabilidades**
- **Arquivo/trecho:** `src/AppManager.js` (classe inteira, linhas 7-150)
- **Descrição:** Uma única classe era responsável por criar/seedar o schema do banco, registrar todas as rotas HTTP e conter toda a regra de negócio (checkout, pagamento, matrícula, relatório).
- **Impacto:** Alto acoplamento, dificuldade de testar isoladamente, mudanças em uma responsabilidade arriscavam quebrar outras.
- **Recomendação:** Separar em Models, Controllers, Services e módulo dedicado de conexão com banco.

**6. [HIGH] Lógica de negócio dentro da definição das rotas**
- **Arquivo/trecho:** `src/AppManager.js:31-85` (rota `/api/checkout`)
- **Descrição:** Decisão de aprovação/recusa de pagamento, criação de usuário, matrícula, registro de pagamento e auditoria eram orquestrados diretamente no callback da rota.
- **Impacto:** Regra de negócio não reutilizável nem testável independentemente da camada HTTP.
- **Recomendação:** Extrair para um Service dedicado; a rota apenas delega e traduz a resposta HTTP.

**7. [MEDIUM] N+1 Queries no relatório financeiro**
- **Arquivo/trecho:** `src/AppManager.js:97-134`
- **Descrição:** Para cada curso, buscava matrículas; para cada matrícula, disparava duas queries adicionais (usuário e pagamento) dentro de `forEach`.
- **Impacto:** Degradação de performance severa conforme a base cresce.
- **Recomendação:** Substituir por uma única query com `JOIN`, agregando os dados na aplicação.

**8. [MEDIUM] Callback hell / aninhamento profundo**
- **Arquivo/trecho:** `src/AppManager.js:41-84`
- **Descrição:** O handler de checkout aninhava `db.get`/`db.run` em 5+ níveis de callbacks.
- **Impacto:** Código difícil de ler, propagação de erro inconsistente, alto risco de bugs em manutenção.
- **Recomendação:** Promisificar as chamadas do banco e reescrever com `async/await`.

**9. [MEDIUM] Tratamento de erros inconsistente**
- **Arquivo/trecho:** `src/AppManager.js:142-145` (`DELETE /api/users/:id` ignorava `err`) vs. demais rotas
- **Descrição:** Algumas rotas verificavam `err` e respondiam com status apropriado; a rota de exclusão de usuário ignorava completamente o erro do `db.run`.
- **Impacto:** Falhas silenciosas, resposta de sucesso mesmo quando a exclusão falhava.
- **Recomendação:** Centralizar tratamento de erros com middleware de erro do Express.

**10. [MEDIUM] Estado global mutável**
- **Arquivo/trecho:** `src/utils.js:11-18` (`globalCache`), uso em `src/AppManager.js:66`
- **Descrição:** `globalCache` era um objeto de módulo mutado a cada requisição, compartilhado entre todas as requisições concorrentes.
- **Impacto:** Condições de corrida, comportamento imprevisível sob concorrência, acoplamento oculto entre requisições.
- **Recomendação:** Remover o estado global ou substituir por cache explícito.

**11. [LOW] Integridade referencial quebrada na exclusão de usuário**
- **Arquivo/trecho:** `src/AppManager.js:139-146`
- **Descrição:** Exclusão de usuário não removia/tratava matrículas e pagamentos associados — o próprio texto de resposta admitia: "matrículas e pagamentos ficaram sujos no banco".
- **Impacto:** Registros órfãos, relatórios financeiros incorretos no futuro.
- **Recomendação:** Tratar a limpeza transacionalmente (cascata) em um Service dedicado.

**12. [LOW] Nomes pouco descritivos e magic strings/values**
- **Arquivo/trecho:** `src/AppManager.js:33-37, 53` (`u`, `e`, `p`, `cid`, `cc`, status `"PAID"`/`"DENIED"`, prefixo mágico `"4"` do cartão)
- **Descrição:** Variáveis de uma letra e literais de string/número espalhados sem constantes nomeadas.
- **Impacto:** Reduz legibilidade e manutenibilidade, aumenta risco de erro ao alterar regra de negócio.
- **Recomendação:** Renomear para nomes completos e extrair constantes nomeadas.

**13. [LOW] Código morto / variável não utilizada**
- **Arquivo/trecho:** `src/utils.js:12,28` (`totalRevenue`)
- **Descrição:** Variável declarada e exportada mas nunca lida ou atualizada de forma significativa.
- **Impacto:** Ruído no código, falsa impressão de funcionalidade existente.
- **Recomendação:** Remover.

---

## Fase 3 — Correções Realizadas

| # | Problema | Correção aplicada |
|---|---|---|
| 1 | Credenciais hardcoded | Extraídas para variáveis de ambiente (`src/config/env.js`, `.env.example`, `.gitignore`); nenhum segredo permanece no código-fonte |
| 2 | Exposição de dados sensíveis em logs | Log do número de cartão e da chave do gateway removido; `paymentGatewayService` não loga dados sensíveis |
| 3 | Hashing inseguro | `badCrypto` substituído por `bcryptjs` (`src/services/passwordService.js`); fallback de senha fraca removido — senha agora é obrigatória para novos usuários (400 se ausente) |
| 4 | Ausência de autenticação em rotas administrativas | Middleware `adminAuth` (`src/middleware/adminAuth.js`) exigindo header `x-admin-key`, aplicado a `GET /api/admin/financial-report` e `DELETE /api/users/:id` |
| 5 | God Class | `AppManager.js` removido; responsabilidades divididas em `models/`, `services/`, `controllers/`, `routes/`, `database/` |
| 6 | Lógica de negócio nas rotas | Extraída para `checkoutService`, `reportService`, `userService`; controllers ficaram finos, apenas traduzindo request/response |
| 7 | N+1 queries | Relatório financeiro reescrito com uma única query `JOIN` (`src/models/reportModel.js`) e agregação em memória |
| 8 | Callback hell | Camada `Database` (`src/database/Database.js`) promisifica `run`/`get`/`all`; todo fluxo de checkout reescrito com `async/await` |
| 9 | Tratamento inconsistente de erros | Middleware central `errorHandler` + classe `AppError` (`src/utils/AppError.js`, `src/middleware/errorHandler.js`) usada em todos os services/controllers |
| 10 | Estado global mutável | `globalCache` e `totalRevenue` removidos completamente (eram código morto/inseguro) |
| 11 | Registros órfãos | `userService.deleteUser` agora remove pagamentos e matrículas associados antes de excluir o usuário (exclusão em cascata) |
| 12 | Magic strings/naming | Constante `PAYMENT_STATUS` (`src/constants/paymentStatus.js`); variáveis internas renomeadas para nomes descritivos (contrato externo dos campos JSON da API preservado: `usr`, `eml`, `pwd`, `c_id`, `card`) |
| 13 | Código morto | `totalRevenue` e configs não utilizadas (`dbUser`, `dbPass`, `smtpUser`) removidas |

### Nova Estrutura Arquitetural (MVC)

```
src/
  app.js                     — composition root
  config/
    env.js                   — configuração via variáveis de ambiente
  database/
    Database.js              — wrapper promisificado do sqlite3
    connection.js             — criação da conexão
    schema.js                 — criação das tabelas
    seed.js                   — dados de seed (senha já hasheada)
  constants/
    paymentStatus.js          — enum PAYMENT_STATUS
  models/
    userModel.js, courseModel.js, enrollmentModel.js,
    paymentModel.js, auditLogModel.js, reportModel.js
  services/
    checkoutService.js, reportService.js, userService.js,
    passwordService.js, paymentGatewayService.js
  controllers/
    checkoutController.js, reportController.js, userController.js
  routes/
    index.js, checkoutRoutes.js, reportRoutes.js, userRoutes.js
  middleware/
    errorHandler.js, adminAuth.js
  utils/
    AppError.js, asyncHandler.js
```

`AppManager.js` e o antigo `utils.js` foram removidos, substituídos pela estrutura acima.

Arquivos de suporte adicionados/atualizados: `.env.example`, `.gitignore`, `package.json` (dependências `bcryptjs` e `dotenv`), `README.md`, `api.http`.

---

## Validações Executadas

1. **Dependências:** `npm install` executado com sucesso (`bcryptjs`, `dotenv`, `express`, `sqlite3`)
2. **Imports/sintaxe:** aplicação carregada sem erros de módulo
3. **Inicialização da aplicação:** `node src/app.js` sobe o servidor na porta configurada sem erros de boot
4. **Conexão com banco:** schema criado e seed executado com sucesso no SQLite em memória
5. **Rotas/endpoints existentes:** todos os 3 endpoints originais preservados (`POST /api/checkout`, `GET /api/admin/financial-report`, `DELETE /api/users/:id`)
6. **Operações principais:** fluxo de checkout (usuário novo/existente, aprovação/recusa de pagamento), geração de relatório financeiro e exclusão de usuário testados manualmente via `curl`

### Resultado dos Testes de Endpoints

| Teste | Requisição | Resultado |
|---|---|---|
| Checkout — usuário novo, pagamento aprovado | `POST /api/checkout` (cartão iniciando com `4`) | `200` — `{"msg":"Sucesso","enrollment_id":2}` |
| Checkout — pagamento recusado | `POST /api/checkout` (cartão iniciando com `5`) | `400` — `"Pagamento recusado"` |
| Checkout — usuário novo sem senha | `POST /api/checkout` (sem `pwd`) | `400` — `"Senha obrigatória para novo usuário"` (fix da senha fraca padrão) |
| Relatório administrativo sem header de auth | `GET /api/admin/financial-report` | `401` (fix da falta de autenticação) |
| Relatório administrativo com header de auth | `GET /api/admin/financial-report` + `x-admin-key` | `200` — JSON correto, sem N+1 (query única) |
| Exclusão de usuário sem header de auth | `DELETE /api/users/1` | `401` (fix da falta de autenticação) |
| Exclusão de usuário com header de auth | `DELETE /api/users/1` + `x-admin-key` | `200` — `"Usuário deletado com sucesso."` |
| Relatório após exclusão do usuário | `GET /api/admin/financial-report` | Curso "Clean Architecture" retornou `revenue: 0` e `students: []` — confirmando que matrículas/pagamentos foram removidos em cascata (fix dos registros órfãos) |

Todos os testes confirmaram que o comportamento e os contratos de entrada/saída da API foram preservados, com exceção da exigência do header `x-admin-key` nas duas rotas administrativas — mudança intencional para corrigir a falha crítica de ausência de autenticação (finding #4).

---

## Conclusão

Todos os 13 findings identificados na Fase 2 foram corrigidos na Fase 3. A aplicação foi migrada de uma estrutura monolítica (God Class) para uma arquitetura MVC em camadas (Models, Services, Controllers, Routes, Middleware, Database, Config), com validação funcional completa via testes manuais de todos os endpoints.
