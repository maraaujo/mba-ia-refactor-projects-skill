# Refactoring Playbook — Padrões de Transformação (Fase 3)

10 padrões de transformação, cada um com problema, estratégia, código antes/depois
e cuidados de validação. Os exemplos alternam entre Python/Flask e Node.js/Express
para deixar claro que a estratégia é a mesma independentemente da stack — adapte a
sintaxe ao idioma detectado na Fase 1, não o padrão em si.

---

## 1. SQL concatenado → query parametrizada

**Problema:** valor de entrada do usuário concatenado diretamente na string SQL,
abrindo espaço para SQL Injection.

**Estratégia:** substituir a concatenação por placeholders do driver/ORM, passando
os valores como parâmetros separados da string SQL.

**Antes (Python/sqlite3):**
```python
def get_usuario_por_email(email):
    query = "SELECT * FROM usuarios WHERE email = '" + email + "'"
    return cursor.execute(query).fetchone()
```

**Depois:**
```python
def get_usuario_por_email(email):
    return cursor.execute(
        "SELECT * FROM usuarios WHERE email = ?", (email,)
    ).fetchone()
```

**Cuidados de validação:** testar com valores contendo aspas simples e payloads
clássicos de injeção (`' OR '1'='1`) e confirmar que são tratados como dado literal,
não como SQL; conferir que o resultado da consulta para casos legítimos não mudou.

---

## 2. Hardcoded secret → variável de ambiente

**Problema:** segredo (chave, senha, token) escrito diretamente no código-fonte.

**Estratégia:** mover o valor para uma variável de ambiente, com leitura
centralizada em um módulo de configuração; nunca commitar o valor real.

**Antes (Node.js):**
```javascript
const config = {
  paymentGatewayKey: "pk_live_1234567890abcdef",
};
```

**Depois:**
```javascript
// src/config/env.js
require('dotenv').config();

const config = {
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY,
};

module.exports = config;
```
```
# .env.example
PAYMENT_GATEWAY_KEY=changeme
```

**Cuidados de validação:** confirmar que a aplicação falha de forma clara (ou usa
um default seguro só para dev) quando a variável não está definida; garantir que
`.env` está no `.gitignore` e que o valor antigo exposto é rotacionado.

---

## 3. God Class → separação em camadas

**Problema:** uma única classe concentra inicialização de banco, rotas e regra de
negócio de múltiplos domínios.

**Estratégia:** identificar os domínios/responsabilidades distintas dentro da
classe e extrair cada um para seu próprio módulo (Model, Service, Controller,
Routes, Database), mantendo o comportamento observável.

**Antes (Node.js):**
```javascript
class AppManager {
  constructor(app) {
    this.app = app;
    this.setupDatabase();
    this.setupRoutes();
  }
  setupDatabase() { /* cria schema, seed */ }
  setupRoutes() {
    this.app.post('/api/checkout', (req, res) => { /* regra de negócio inline */ });
    this.app.get('/api/admin/financial-report', (req, res) => { /* N+1, sem auth */ });
  }
}
```

**Depois:**
```javascript
// database/schema.js, database/seed.js  → inicialização do banco
// services/checkoutService.js            → regra de negócio de checkout
// services/reportService.js              → regra de negócio de relatório
// controllers/checkoutController.js      → tradução HTTP <-> checkoutService
// routes/checkoutRoutes.js               → router.post('/checkout', checkoutController.create)
// app.js (composition root)
const app = express();
app.use('/api', routes);
```

**Cuidados de validação:** cada endpoint original deve continuar respondendo com o
mesmo contrato de entrada/saída; testar todos os endpoints antes/depois da divisão.

---

## 4. Lógica de negócio em route/controller → service

**Problema:** decisão de negócio implementada diretamente no handler da rota.

**Estratégia:** extrair a regra para uma função de serviço pura, que recebe dados
já parseados e devolve um resultado ou lança uma exceção de domínio; o controller
passa a apenas chamar o serviço.

**Antes (Python/Flask):**
```python
@app.route("/produtos", methods=["POST"])
def criar_produto():
    dados = request.json
    if not dados.get("nome") or len(dados["nome"]) < 3:
        return {"erro": "nome inválido"}, 400
    if dados.get("preco", 0) <= 0:
        return {"erro": "preço inválido"}, 400
    produto_id = db_insert_produto(dados)
    return {"id": produto_id}, 201
```

**Depois:**
```python
# services/produto_service.py
def criar_produto(dados):
    _validar_dados_produto(dados)
    return ProdutoModel.criar(dados)

# controllers/produto_controller.py
def criar_produto():
    try:
        produto_id = produto_service.criar_produto(request.json)
        return jsonify(id=produto_id), 201
    except ValidationError as e:
        return jsonify(erro=str(e)), 400
```

**Cuidados de validação:** cobrir os mesmos casos de validação testados
manualmente antes da extração (dados válidos, inválidos, ausentes) e confirmar que
os códigos de status HTTP não mudaram.

---

## 5. Global mutable state → ciclo de vida/contexto/injeção

**Problema:** variável de módulo mutada a cada requisição, compartilhada de forma
insegura entre requisições concorrentes.

**Estratégia:** mover o estado para o escopo da requisição (contexto do framework)
ou para uma estrutura de cache explícita com regras de concorrência definidas; se
o estado não for de fato utilizado, removê-lo.

**Antes (Python/Flask):**
```python
conexao_db = None

def get_db():
    global conexao_db
    if conexao_db is None:
        conexao_db = sqlite3.connect(DB_PATH)
    return conexao_db
```

**Depois:**
```python
from flask import g

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
    return g.db

@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
```

**Cuidados de validação:** testar requisições concorrentes/sequenciais e confirmar
ausência de dados vazando entre requisições distintas; verificar que a conexão é
corretamente fechada ao final de cada requisição.

---

## 6. N+1 → JOIN/batch loading

**Problema:** uma query adicional é disparada para cada item de uma coleção dentro
de um loop.

**Estratégia:** substituir por uma única query com `JOIN` (ou eager loading do ORM)
que já traz os dados relacionados, eliminando as consultas repetidas.

**Antes (Python/SQLAlchemy):**
```python
tasks = Task.query.all()
resultado = []
for t in tasks:
    usuario = User.query.get(t.user_id)   # query extra por item
    resultado.append({"titulo": t.title, "usuario": usuario.name})
```

**Depois:**
```python
tasks = Task.query.options(joinedload(Task.user)).all()
resultado = [{"titulo": t.title, "usuario": t.user.name} for t in tasks]
```

**Cuidados de validação:** comparar o número de queries executadas antes/depois
(log de SQL ou profiler) e confirmar que o resultado retornado é idêntico ao
comportamento anterior.

---

## 7. Tratamento repetido de erro → handler centralizado

**Problema:** cada rota implementa seu próprio `try/except`/callback de erro, de
forma inconsistente (algumas tratam, outras ignoram o erro).

**Estratégia:** definir exceções de domínio e um único ponto de tratamento
(error handler global) que traduz qualquer exceção não tratada em uma resposta
HTTP padronizada.

**Antes (Node.js):**
```javascript
app.delete('/api/users/:id', (req, res) => {
  db.run('DELETE FROM users WHERE id = ?', [req.params.id], (err) => {
    res.json({ msg: 'Usuário deletado com sucesso.' }); // err ignorado
  });
});
```

**Depois:**
```javascript
// middleware/errorHandler.js
function errorHandler(err, req, res, next) {
  const status = err.status || 500;
  res.status(status).json({ erro: err.message });
}

// controllers/userController.js
async function deleteUser(req, res, next) {
  try {
    await userService.deleteUser(req.params.id);
    res.json({ msg: 'Usuário deletado com sucesso.' });
  } catch (err) {
    next(err);
  }
}
```

**Cuidados de validação:** forçar deliberadamente um erro (ex.: id inexistente, ou
falha simulada de banco) e confirmar que a resposta de erro é consistente e que o
erro não é mais silenciado.

---

## 8. Deprecated API → alternativa moderna

**Problema:** uso de método/API marcado como obsoleto pela documentação oficial da
versão em uso.

**Estratégia:** substituir pela alternativa recomendada, preservando o mesmo
comportamento observável (mesmo formato de dado, mesmo fuso horário, etc.).

**Antes (Python 3.12 + SQLAlchemy 2.x):**
```python
usuario = User.query.get(user_id)
criado_em = datetime.utcnow()
```

**Depois:**
```python
usuario = db.session.get(User, user_id)
criado_em = datetime.now(timezone.utc)
```

**Cuidados de validação:** confirmar que nenhum warning de depreciação é mais
emitido na execução; se o valor antigo era "naive" (sem timezone) e persistido
assim, garantir compatibilidade com os dados já armazenados (ex.: convertendo de
volta para naive antes de salvar, se necessário).

---

## 9. Magic numbers/strings → constants/enums

**Problema:** valores literais com significado de negócio repetidos pelo código
sem uma constante nomeada.

**Estratégia:** centralizar os valores em um módulo de constantes (ou enum) e
substituir todas as ocorrências literais por referências a essa constante.

**Antes (Python):**
```python
if categoria not in ["eletronicos", "roupas", "alimentos", "livros"]:
    return {"erro": "categoria inválida"}, 400
```

**Depois:**
```python
# constants.py
CATEGORIAS_VALIDAS = ["eletronicos", "roupas", "alimentos", "livros"]

# controllers/produto_controller.py
from constants import CATEGORIAS_VALIDAS

if categoria not in CATEGORIAS_VALIDAS:
    return {"erro": "categoria inválida"}, 400
```

**Cuidados de validação:** garantir que todos os pontos do código que usavam o
literal passam a referenciar a constante (evitar deixar uma ocorrência antiga
divergente) e que o comportamento de validação não mudou.

---

## 10. Callbacks aninhados → async/await (quando aplicável)

**Problema:** múltiplos níveis de callback aninhados para operações assíncronas
sequenciais, dificultando leitura e propagação de erro.

**Estratégia:** promisificar as chamadas assíncronas e reescrever o fluxo com
`async/await`, propagando erros com `try/catch` (ou middleware assíncrono).

**Antes (Node.js):**
```javascript
db.get('SELECT * FROM users WHERE email = ?', [email], (err, user) => {
  if (err) return res.status(500).json({ erro: err.message });
  if (!user) {
    db.run('INSERT INTO users (email) VALUES (?)', [email], function (err2) {
      if (err2) return res.status(500).json({ erro: err2.message });
      db.run('INSERT INTO enrollments (user_id) VALUES (?)', [this.lastID], (err3) => {
        if (err3) return res.status(500).json({ erro: err3.message });
        res.json({ msg: 'ok' });
      });
    });
  }
});
```

**Depois:**
```javascript
async function checkout(req, res, next) {
  try {
    let user = await userModel.findByEmail(req.body.email);
    if (!user) user = await userModel.create({ email: req.body.email });
    await enrollmentModel.create({ userId: user.id });
    res.json({ msg: 'ok' });
  } catch (err) {
    next(err);
  }
}
```

**Cuidados de validação:** testar o fluxo completo (caminho feliz e cada ponto de
falha simulada) e confirmar que os erros continuam sendo propagados/tratados
corretamente pelo handler centralizado (ver padrão 7), sem falhas silenciosas.

**Nota de aplicabilidade:** este padrão só se aplica a linguagens/runtimes com
callbacks assíncronos baseados em I/O não bloqueante (ex.: Node.js). Em frameworks
Python síncronos (Flask/WSGI) este problema específico não ocorre da mesma forma —
não force `async/await` onde a stack detectada não o justificar.
