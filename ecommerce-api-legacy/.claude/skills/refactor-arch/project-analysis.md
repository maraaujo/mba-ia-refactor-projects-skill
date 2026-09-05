# Project Analysis — Heurísticas de Detecção (Fase 1)

Este arquivo fornece heurísticas para a Fase 1 (`SKILL.md`). O objetivo é identificar
a stack e a arquitetura atual **a partir da evidência nos arquivos do projeto**,
nunca por suposição. Se um sinal não estiver presente, não afirme a conclusão —
diga que não foi possível confirmar.

A abordagem é agnóstica de tecnologia: as heurísticas abaixo cobrem Python/Flask e
Node.js/Express (as stacks usadas neste desafio), mas o método (procurar arquivos de
manifesto, extensões predominantes, imports/requires no entry point) se generaliza
para qualquer linguagem/framework.

---

## 1. Linguagem

Sinal primário: extensão predominante dos arquivos de código-fonte (ignorando
diretórios de dependências como `node_modules/`, `venv/`, `.venv/`, `__pycache__/`).

| Extensão predominante | Linguagem provável |
|---|---|
| `.py` | Python |
| `.js` / `.mjs` / `.cjs` | JavaScript (Node.js) |
| `.ts` | TypeScript |
| `.rb` | Ruby |
| `.go` | Go |
| `.java` | Java |

Sinal secundário (desempate ou confirmação): arquivo de manifesto de dependências
na raiz do projeto — `requirements.txt` / `pyproject.toml` / `Pipfile` (Python),
`package.json` (Node.js), `Gemfile` (Ruby), `go.mod` (Go), `pom.xml`/`build.gradle` (Java).

## 2. Framework

Não assuma o framework pelo nome do projeto ou pela pasta. Confirme por import/require
explícito no entry point ou por dependência declarada no manifesto.

**Python:**
- `from flask import Flask` / `Flask(__name__)` → Flask
- `from django...` / `manage.py` na raiz → Django
- `from fastapi import FastAPI` → FastAPI
- Versão: procurar `flask==X.Y.Z` (ou equivalente) em `requirements.txt`/`pyproject.toml`.

**Node.js:**
- `require('express')` / `import express from 'express'` → Express
- `"express"` em `dependencies` no `package.json` → confirma a versão
- `require('koa')` → Koa; `@nestjs/core` → NestJS

Se nenhum framework web for encontrado mas houver um servidor HTTP manual
(`http.createServer` em Node, `wsgiref` em Python), classifique como
"sem framework — servidor HTTP nativo" em vez de adivinhar um framework.

## 3. Banco de dados e ORM/biblioteca de persistência

Procure nesta ordem:

1. **Driver nativo sem ORM:**
   - Python: `import sqlite3`, `import psycopg2`, `import pymysql`
   - Node.js: `require('sqlite3')`, `require('pg')`, `require('mysql2')`
   - Sinal de ausência de ORM: chamadas diretas como `cursor.execute(...)` /
     `db.get(...)`/`db.run(...)`/`db.all(...)` com SQL escrito manualmente.
2. **ORM:**
   - Python: `Flask-SQLAlchemy` / `SQLAlchemy` (`db = SQLAlchemy(app)`, classes
     herdando de `db.Model`), Django ORM (`models.Model`), Peewee.
   - Node.js: Sequelize, Prisma (`schema.prisma`), TypeORM, Mongoose (MongoDB).
3. **Arquivo/host do banco:** procure strings de conexão, caminho de arquivo
   (`*.db`, `*.sqlite`), ou `:memory:` (SQLite em memória — comum em ambientes de
   teste/demo, relevante para a Fase 1 registrar como tal).

Distinga explicitamente "usa ORM" de "usa driver nativo com SQL manual" — isso
muda o que a Fase 2 deve procurar (SQL Injection é uma preocupação direta apenas
quando há SQL manual construído a partir de input).

## 4. Entry point

- Python/Flask: arquivo que chama `Flask(__name__)`/`app.run(...)` ou expõe uma
  função `create_app()` (application factory). Normalmente `app.py` ou `wsgi.py`.
- Node.js/Express: arquivo que chama `express()` e `app.listen(...)`. Verifique
  também o campo `"main"` e o script `"start"` em `package.json`, pois podem
  apontar para o entry point real (ex.: `src/app.js`).

## 5. Arquitetura atual

Para mapear a arquitetura existente, verifique a presença **e o uso real** dos
seguintes elementos (não basta a pasta existir — confirme se o conteúdo cumpre o
papel esperado da camada):

- **Models:** módulo(s) responsável(is) por representar entidades e acessar dados
  (classes ORM, ou funções que executam queries).
- **Views/Routes:** definição de endpoints HTTP (`@app.route(...)`, `Blueprint`,
  `router.get(...)`, `app.post(...)`).
- **Controllers:** funções/classes que traduzem request → chamada de negócio →
  response, sem conter a regra de negócio nem SQL diretamente.
- **Services:** módulos com regra de negócio pura, chamáveis independentemente do
  transporte HTTP.
- **Configuração:** arquivo dedicado a configuração (`config.py`, `.env`, `env.js`)
  vs. valores hardcoded espalhados pelo código.
- **Utilitários/testes:** pasta `utils/`/`helpers/`, pasta `tests/`.

**Sinal de arquitetura monolítica/sem camadas:** poucos arquivos na raiz
concentrando rotas + regra de negócio + acesso a dados no mesmo arquivo ou classe
(ex.: uma única classe grande responsável por tudo).

**Sinal de "pseudo-MVC":** as pastas `models/`, `routes/`, `services/` existem,
mas ao ler o conteúdo de `routes/*`, a lógica de validação e regra de negócio está
implementada ali mesmo (não delegada a `services/`), e/ou `services/` existe mas
não é chamado pelas rotas. Isso deve ser registrado como problema arquitetural
mesmo que a estrutura de pastas "pareça" organizada — a estrutura de diretórios
por si só não garante separação de responsabilidades.

## 6. Sinais para diferenciar Python/Flask vs. Node.js/Express

| Sinal | Flask (Python) | Express (Node.js) |
|---|---|---|
| Manifesto de dependências | `requirements.txt` / `pyproject.toml` | `package.json` |
| Import do framework | `from flask import Flask, request, jsonify` | `const express = require('express')` |
| Registro de rota | `@app.route('/x', methods=['GET'])` ou `Blueprint` | `router.get('/x', handler)` / `app.get('/x', handler)` |
| Objeto de request | `request.json`, `request.args` | `req.body`, `req.query` |
| Objeto de response | `jsonify(...)`, `return dict, status` | `res.json(...)`, `res.status(...).send(...)` |
| Middleware | `@app.before_request`, `@app.errorhandler` | `app.use(middlewareFn)` |
| Concorrência de I/O | síncrono por padrão (WSGI) | assíncrono por padrão (callbacks/Promises/`async-await`) — relevante para detectar "callback hell" |

## 7. Abordagem agnóstica de tecnologia

- Nunca assuma a stack pelo nome da pasta ou pelo domínio de negócio do projeto —
  confirme sempre pelos sinais acima.
- Ao descrever a arquitetura atual e propor a arquitetura alvo (Fase 3), use os
  nomes de camada conceituais (Models, Views/Routes, Controllers, Services,
  configuração, acesso a dados, middlewares, tratamento de erros, entry point) e
  só então traduza para a convenção idiomática da linguagem detectada (ex.:
  `services/` como pasta em Python e Node.js, mas `errors.py` + `@app.errorhandler`
  em Flask vs. `errorHandler.js` como middleware do Express).
- Não force um padrão de nomenclatura de uma stack sobre outra (ex.: não crie
  `Controller.js` estilo Java em um projeto Flask, nem `views.py` estilo Django em
  um projeto Express).
