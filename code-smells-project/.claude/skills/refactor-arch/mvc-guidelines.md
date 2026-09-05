# MVC Guidelines — Arquitetura Alvo da Refatoração (Fase 3)

Estas guidelines definem a arquitetura MVC (+ Service layer) alvo da Fase 3, de
forma agnóstica de tecnologia. Cada camada é descrita pelo seu propósito e pelas
responsabilidades permitidas/proibidas, e só depois traduzida para convenções
concretas de Flask e Express — nenhuma das duas stacks é tratada como padrão
"principal" e a outra como adaptação.

---

## Camadas

### Models

- **Responsabilidade permitida:** representar entidades de domínio e executar o
  acesso a dados correspondente (queries parametrizadas, ou mapeamento ORM).
  Pode conter validação estrutural mínima do próprio dado (ex.: um método que
  calcula se a entidade está "atrasada" a partir de seus próprios campos).
- **Proibido:** orquestrar múltiplas entidades não relacionadas, conter lógica de
  fluxo HTTP, ou chamar Controllers/Routes.
- **Flask:** classes SQLAlchemy (`db.Model`) ou módulo `models/<entidade>_model.py`
  com funções que encapsulam queries ao driver nativo.
- **Express:** módulo `models/<entidade>Model.js` com funções que encapsulam
  queries ao driver de banco (nativo ou ORM).

### Views / Routes

- **Responsabilidade permitida:** declarar os endpoints (método HTTP + path) e
  delegar imediatamente para o Controller correspondente. Em APIs REST, "View" é
  a própria representação JSON de saída — não um template renderizado.
- **Proibido:** conter lógica de negócio, acesso direto a dados, ou validação de
  regra de domínio.
- **Flask:** `Blueprint`/`@app.route(...)` em `routes.py` ou `routes/`.
- **Express:** `express.Router()` em `routes/`.

### Controllers

- **Responsabilidade permitida:** traduzir a requisição HTTP em uma chamada ao
  Service apropriado, e traduzir o retorno do Service em uma resposta HTTP
  (status code, corpo, headers). Parsing e validação de formato de request (ex.:
  "o campo existe no JSON?") são responsabilidade legítima do Controller.
- **Proibido:** conter regra de negócio, cálculos de domínio, ou acesso direto ao
  banco de dados.
- **Flask:** funções em `controllers/<dominio>_controller.py`, registradas nas
  rotas de `routes.py`.
- **Express:** funções/classes em `controllers/<dominio>Controller.js`.

### Services

- **Quando necessário:** sempre que existir regra de negócio não trivial —
  cálculos, decisões condicionais de domínio, orquestração de múltiplas
  operações/models. Para CRUDs verdadeiramente triviais (sem regra alguma além de
  "salvar o que veio"), um Service fino que apenas delega ao Model ainda é
  recomendado, para manter o Controller consistente e testável.
- **Responsabilidade permitida:** toda a lógica de negócio, validação de domínio,
  orquestração entre Models, chamadas a serviços externos (ex.: gateway de
  pagamento, envio de e-mail).
- **Proibido:** conhecer detalhes de transporte HTTP (não deve receber/retornar
  objetos de request/response do framework web).
- **Flask/Express:** módulo `services/<dominio>_service.py` / `<dominio>Service.js`.

### Configuração

- **Responsabilidade permitida:** ler configuração de variáveis de ambiente
  (com valores padrão sensatos apenas para desenvolvimento) e expor um objeto/
  função de configuração único para o restante da aplicação.
- **Proibido:** conter segredos reais hardcoded, ou ser lida diretamente por
  Models/Controllers sem passar pelo módulo de config (evita configuração
  duplicada/inconsistente).
- **Flask:** `config.py` (classe `Config` ou função que lê `os.environ`).
- **Express:** `config/env.js` (lê `process.env`, idealmente via `dotenv`).

### Acesso a dados

- **Responsabilidade permitida:** estabelecer e gerenciar a conexão/pool com o
  banco de dados, schema/migrations, seed de dados.
- **Proibido:** conter regra de negócio ou ser instanciado de forma que crie
  estado global mutável compartilhado incorretamente entre requisições
  concorrentes (ver `anti-patterns.md#6-global-mutable-state`).
- **Flask:** `database.py` (conexão por contexto de requisição, ex. `flask.g`) +
  `schema.py` (DDL).
- **Express:** `database/connection.js` + `database/schema.js` (+ wrapper
  promisificado do driver, se o driver nativo for baseado em callback).

### Middlewares

- **Responsabilidade permitida:** cross-cutting concerns aplicados antes/depois do
  Controller — autenticação/autorização, CORS, logging de requisição.
- **Proibido:** conter regra de negócio específica de um único endpoint.
- **Flask:** `@app.before_request`, decorators aplicados às rotas (`middleware.py`).
- **Express:** funções `(req, res, next) => {...}` registradas com `app.use(...)`
  ou por rota (`middleware/`).

### Error handling

- **Responsabilidade permitida:** capturar exceções de domínio (e, no nível mais
  alto, qualquer exceção não tratada) e traduzi-las para uma resposta HTTP
  padronizada, uma única vez, centralizadamente.
- **Proibido:** tratamento de erro duplicado e divergente em cada rota (ver
  `anti-patterns.md#9-inconsistent-error-handling`).
- **Flask:** exceções de domínio + `@app.errorhandler(...)` em `errors.py`.
- **Express:** classe de erro (`AppError`) + middleware de erro final
  (`app.use((err, req, res, next) => ...)`) em `middleware/errorHandler.js`.

### Composition root / entry point

- **Responsabilidade permitida:** instanciar a aplicação, registrar rotas,
  middlewares e error handlers, e iniciar o servidor. É o único lugar onde todas
  as camadas são "amarradas" umas às outras.
- **Proibido:** conter lógica de negócio ou definição de rota inline.
- **Flask:** `app.py` com `create_app()` (application factory).
- **Express:** `app.js` (ou `src/app.js`), registrando `routes/index.js`.

---

## Resumo — Permitido x Proibido por camada

| Camada | Pode | Não pode |
|---|---|---|
| Models | Acesso a dados, validação estrutural do próprio dado | Lógica de negócio multi-entidade, HTTP |
| Views/Routes | Declarar endpoint, delegar ao Controller | Lógica de negócio, acesso a dados |
| Controllers | Parse de request, chamada ao Service, montagem de response | Regra de negócio, SQL/queries diretas |
| Services | Regra de negócio, orquestração, chamadas externas | Objetos de request/response do framework web |
| Config | Ler env vars, expor config tipada | Segredos hardcoded |
| Acesso a dados | Conexão, schema, seed | Regra de negócio |
| Middlewares | Cross-cutting concerns (auth, CORS, log) | Regra de negócio específica de 1 endpoint |
| Error handling | Tradução centralizada de exceção → resposta HTTP | Tratamento duplicado por rota |
| Entry point | Composição da aplicação, boot | Lógica de negócio, rotas inline |

## Adaptação a Flask e Express sem acoplamento exclusivo

- A separação acima é a mesma nas duas stacks — o que muda é apenas a convenção
  de arquivo/pasta e a forma idiomática de implementar cada camada (decorators e
  `flask.g` em Flask; `Router`/middleware de erro em Express).
- Não exija que um projeto Node.js tenha uma pasta `views/` no sentido Django/Rails
  (templates server-side) — em uma API REST, "View" é a serialização JSON, e pode
  viver dentro do próprio Controller ou de um serializer dedicado.
- Não exija `Blueprint` em um projeto Express nem `Router` em um projeto Flask —
  use o mecanismo de roteamento nativo de cada framework.
- Quando o projeto já tiver alguma estrutura parcial (ex.: `routes/`, `services/`
  existentes mas mal utilizados), a Fase 3 deve reorganizar o conteúdo dentro da
  estrutura já convencionada pelo projeto sempre que possível, em vez de impor uma
  estrutura nova do zero.
