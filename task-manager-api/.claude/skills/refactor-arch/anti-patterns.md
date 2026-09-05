# Catálogo de Anti-Patterns e Code Smells (Fase 2)

Este catálogo é consultado na Fase 2 (`SKILL.md`). Contém 13 anti-patterns, com
severidade distribuída entre CRITICAL, HIGH, MEDIUM e LOW.

**Regra geral:** classifique pelo impacto real observado no código, nunca apenas
pelo nome do padrão. A "severidade sugerida" abaixo é o ponto de partida — ajuste
para cima ou para baixo conforme o contexto (ex.: uma credencial hardcoded em um
projeto de exemplo/seed pode pesar menos do que uma chave de gateway de pagamento
de produção).

---

## 1. Hardcoded Credentials

- **Severidade sugerida:** CRITICAL
- **Descrição:** senhas, chaves de API, tokens ou strings de conexão de banco
  escritos diretamente no código-fonte e versionados no repositório.
- **Sinais de detecção:** literais de string atribuídos a variáveis como
  `SECRET_KEY`, `password`, `db_pass`, `api_key`, `token`; strings de conexão
  completas (`user:senha@host`) embutidas no código.
- **Falsos positivos a evitar:** um **nome** de variável de ambiente (ex.:
  `os.environ["SECRET_KEY"]`) não é uma credencial hardcoded — é o padrão correto.
  Valores de exemplo claramente identificados como placeholder em arquivos
  `.env.example` (que não sobem para produção) não contam como o mesmo problema.
- **Recomendação:** mover para variáveis de ambiente (`.env` + `python-dotenv` /
  `dotenv`), nunca commitar segredos reais, adicionar `.env` ao `.gitignore`,
  rotacionar qualquer chave já exposta.

## 2. SQL Injection

- **Severidade sugerida:** CRITICAL
- **Descrição:** construção de comandos SQL por concatenação/interpolação direta
  de valores vindos do usuário (query string, corpo da requisição, headers).
- **Sinais de detecção:** f-strings, `+`, `%`, ou `.format()` combinando SQL com
  variáveis de request dentro de `execute(...)`.
- **Falsos positivos a evitar (explícito):**
  - **SQL fixo (sem nenhuma variável de entrada do usuário) não é SQL Injection.**
  - **Query parametrizada (`?`, `%s`, `:nome`, bind parameters do ORM) não é SQL
    Injection**, mesmo que monte a query dinamicamente por partes, desde que os
    *valores* continuem passados como parâmetros e não concatenados na string SQL.
- **Recomendação:** usar sempre placeholders/parâmetros do driver ou do ORM;
  nunca interpolar valor de usuário diretamente na string SQL.

## 3. Arbitrary SQL Execution

- **Severidade sugerida:** CRITICAL
- **Descrição:** endpoint que recebe SQL arbitrário do cliente (ex.: campo `sql`
  no corpo da requisição) e o executa sem qualquer whitelist/restrição — vai além
  do SQL Injection clássico porque o próprio comando, não apenas um valor, é
  controlado pelo atacante.
- **Sinais de detecção:** `cursor.execute(request_body["sql"])` ou equivalente;
  endpoints administrativos/"debug" que expõem uma via de execução de query livre.
- **Falsos positivos a evitar:** um endpoint que executa uma das N queries
  fixas pré-definidas no servidor, selecionadas por um identificador validado
  (não pelo texto da query em si), não é execução arbitrária de SQL.
- **Recomendação:** remover o endpoint; se a funcionalidade for genuinamente
  necessária, substituir por operações específicas e auditáveis, nunca por SQL
  livre vindo do cliente.

## 4. God Class / God Method

- **Severidade sugerida:** CRITICAL (quando concentra banco + rotas + regra de
  negócio no mesmo arquivo/classe) — pode cair para HIGH se a concentração for
  parcial (ex.: só regra de negócio + banco, sem roteamento).
- **Descrição:** uma única classe, módulo ou função concentra múltiplas
  responsabilidades não relacionadas (inicialização de banco, definição de rotas,
  regra de negócio, validação, formatação de resposta).
- **Sinais de detecção:** um arquivo/classe com centenas de linhas cobrindo
  domínios diferentes; um método com muitos níveis de responsabilidade
  (valida → consulta banco → calcula → formata → loga → responde) sem nenhuma
  extração para função/módulo auxiliar.
- **Falsos positivos a evitar:** um arquivo grande mas coeso (todas as funções
  pertencem claramente ao mesmo domínio único, ex.: só formatação de datas) não é
  necessariamente uma God Class — avalie coesão, não apenas tamanho.
- **Recomendação:** separar por responsabilidade em Models, Controllers, Services,
  módulo de banco/config dedicados.

## 5. Business Logic in Routes/Controllers

- **Severidade sugerida:** HIGH
- **Descrição:** regras de negócio (cálculos, decisões de aprovação/recusa,
  orquestração de múltiplas operações) implementadas diretamente no handler da
  rota ou no controller, em vez de delegadas a uma camada de serviço.
- **Sinais de detecção:** blocos de `if/else` com regra de domínio dentro do
  callback/handler da rota; cálculos de negócio (total de pedido, desconto,
  aprovação de pagamento) feitos inline no controller.
- **Falsos positivos a evitar:** tradução simples de request/response (parsear
  JSON, montar o dicionário de saída, mapear status HTTP) não é lógica de negócio
  — é responsabilidade legítima do controller.
- **Recomendação:** extrair a regra para uma função/classe de serviço testável
  isoladamente; o controller deve apenas parsear a request, chamar o serviço e
  traduzir o retorno em resposta HTTP.

## 6. Global Mutable State

- **Severidade sugerida:** HIGH
- **Descrição:** estado compartilhado em variável de módulo (cache, contador,
  conexão) que é mutado por múltiplas requisições concorrentes, fora do ciclo de
  vida da requisição.
- **Sinais de detecção:** variável definida no escopo do módulo e reatribuída
  dentro de um handler de rota (`globalCache[...] = ...`, `total += ...`, conexão
  de banco guardada em variável global em vez de por-requisição/pool).
- **Falsos positivos a evitar:** constantes verdadeiramente imutáveis definidas no
  escopo do módulo (listas de valores válidos, configuração carregada uma vez no
  boot e nunca reatribuída) não são estado mutável.
- **Recomendação:** usar contexto de requisição (`flask.g`, middleware de
  request-scope no Express), injeção de dependência, ou um cache explícito com
  ciclo de vida e concorrência bem definidos.

## 7. N+1 Queries

- **Severidade sugerida:** MEDIUM (pode subir para HIGH se o volume de dados
  envolvido for grande e o endpoint for de uso frequente).
- **Descrição:** para cada item de uma coleção obtida por uma query, o código
  dispara uma ou mais queries adicionais dentro do loop, em vez de buscar tudo em
  uma operação (`JOIN`, `IN (...)`, eager loading).
- **Sinais de detecção (explícito):** **N+1 exige consultas adicionais
  executadas repetidamente durante uma iteração** — uma query dentro de um
  `for`/`forEach`/list comprehension que itera sobre resultados de outra query.
- **Falsos positivos a evitar (explícito):** **um loop comum não é N+1.** Um loop
  que apenas transforma dados já carregados em memória (formatação, soma,
  filtragem) sem nenhuma chamada ao banco dentro dele não é N+1.
- **Recomendação:** substituir por uma única query com `JOIN`/agregação, ou usar
  eager loading do ORM (`joinedload`/`selectinload` no SQLAlchemy, `include` no
  Sequelize/Prisma).

## 8. Duplicated Code

- **Severidade sugerida:** MEDIUM
- **Descrição:** a mesma regra de negócio, validação ou query é reimplementada em
  múltiplos lugares, com risco de divergirem ao longo do tempo.
- **Sinais de detecção:** blocos de validação quase idênticos entre `create` e
  `update`; a mesma condição de negócio (ex.: regra de "atrasado") repetida em
  vários arquivos em vez de centralizada em um único método/função reutilizado.
- **Falsos positivos a evitar:** duas funções que fazem operações parecidas mas
  sobre domínios genuinamente diferentes (ex.: validar e-mail de usuário vs.
  validar formato de SKU de produto) não são duplicação — são coincidência de
  forma, não de regra de negócio.
- **Recomendação:** extrair para uma função/constante única e reutilizá-la em
  todos os pontos de uso.

## 9. Inconsistent Error Handling

- **Severidade sugerida:** MEDIUM
- **Descrição:** tratamento de erros divergente entre rotas equivalentes — algumas
  verificam e traduzem o erro corretamente, outras o ignoram (`except: pass`,
  callback que não checa `err`) ou vazam detalhes internos (stack trace, mensagem
  de exceção crua) na resposta ao cliente.
- **Sinais de detecção:** `except:` genérico sem tratamento; callback de banco cujo
  primeiro parâmetro de erro é ignorado; `try/except` repetido em cada rota com
  lógica de resposta diferente para o mesmo tipo de falha.
- **Falsos positivos a evitar:** um único `try/except` específico e intencional
  (ex.: capturar `IntegrityError` para devolver 409) não é inconsistente só por
  existir — o problema é a *divergência* de comportamento para o mesmo tipo de
  erro em pontos equivalentes do código.
- **Recomendação:** centralizar em um error handler global (`@app.errorhandler`
  no Flask, middleware de erro no Express) e usar exceções de domínio específicas.

## 10. Missing Input Validation

- **Severidade sugerida:** MEDIUM (sobe para HIGH se a ausência de validação
  permitir corromper dados ou contornar uma regra de negócio crítica).
- **Descrição:** endpoint aceita e persiste dados sem validar tipo, formato,
  tamanho ou obrigatoriedade dos campos.
- **Sinais de detecção:** campos usados diretamente do corpo da requisição sem
  checagem (`request.json["email"]` usado sem validar formato) antes de salvar.
- **Falsos positivos a evitar:** campos verdadeiramente opcionais que o código já
  trata com default sensato não são "validação ausente".
- **Recomendação:** validar no limite do sistema (camada de serviço ou schema de
  validação) antes de qualquer persistência, com erros 400 claros para o cliente.

## 11. Deprecated APIs

- **Severidade sugerida:** LOW (pode subir para MEDIUM se a API já estiver
  agendada para remoção em versão próxima ou já causar warnings em produção).
- **Descrição:** uso de função/método/biblioteca marcado como obsoleto pela
  própria documentação oficial da linguagem/framework/biblioteca em uso.
- **Sinais de detecção (explícito):** **só reporte com evidência concreta** —
  warning de depreciação emitido em runtime, ou a própria documentação oficial da
  versão instalada (confirmável pelo número de versão no manifesto de
  dependências) declarando o método como deprecated. Exemplos conhecidos: SQLAlchemy
  2.x recomenda `Session.get(Model, id)` no lugar de `Query.get(id)`; Python 3.12
  depreca `datetime.utcnow()` em favor de `datetime.now(timezone.utc)`.
- **Falsos positivos a evitar:** uma API apenas "antiga" ou "não é a forma mais
  moderna de se escrever" mas sem depreciação formal declarada não deve ser
  reportada como deprecated — nesse caso, é no máximo um problema de estilo.
- **Recomendação:** substituir pela alternativa recomendada na documentação
  oficial da versão em uso, preservando o comportamento observável.

## 12. Magic Numbers / Magic Strings

- **Severidade sugerida:** LOW
- **Descrição:** valores literais (números ou strings) com significado de negócio
  espalhados pelo código sem uma constante nomeada, especialmente quando repetidos
  em múltiplos lugares.
- **Sinais de detecção:** comparações como `if status == "pago"` ou
  `if len(nome) < 3` repetidas em vários arquivos, ou uma constante já declarada em
  algum lugar do projeto mas ignorada em favor do literal.
- **Falsos positivos a evitar:** um literal usado uma única vez, cujo significado é
  óbvio no contexto imediato (ex.: `range(1, 13)` para meses do ano), não exige
  necessariamente uma constante nomeada.
- **Recomendação:** centralizar em um módulo de constantes/enum e referenciá-lo em
  todos os pontos de uso.

## 13. Poor Naming

- **Severidade sugerida:** LOW
- **Descrição:** identificadores (variáveis, funções, parâmetros) sem significado
  claro, prejudicando a legibilidade e aumentando o risco de erro ao alterar a
  regra de negócio.
- **Sinais de detecção:** variáveis de uma letra fora de escopos triviais
  (`u`, `e`, `p`, `cid`), abreviações não óbvias sem contexto.
- **Falsos positivos a evitar:** convenções curtas e amplamente aceitas em escopo
  muito reduzido (`i`/`j` em um loop de poucas linhas, `e` em um `except Exception as e`
  usado só para logar) não são, isoladamente, um problema de nomenclatura.
- **Recomendação:** renomear para nomes que expressem o papel da variável/função no
  domínio de negócio.
