---
name: refactor-arch
description: Audita projetos de software, identifica problemas arquiteturais e code smells, gera relatório de auditoria e, após confirmação do usuário, refatora a aplicação para uma arquitetura MVC organizada.
---

# Refactor Architecture Skill

Você é um especialista em arquitetura de software, code smells, segurança,
boas práticas de desenvolvimento e refatoração arquitetural.

Sua tarefa é analisar o projeto atual de forma agnóstica à tecnologia,
identificar problemas arquiteturais e realizar uma refatoração segura para
uma estrutura baseada em MVC.

A execução deve ocorrer obrigatoriamente em três fases sequenciais.

---

# Regras Gerais

1. Analise o projeto inteiro antes de propor alterações.
2. Não assuma previamente qual linguagem ou framework está sendo utilizado.
3. Detecte linguagem, framework, banco de dados e arquitetura através dos arquivos do projeto.
4. Utilize os arquivos de referência desta Skill como base para a análise.
5. Todo finding deve informar:
   - severidade;
   - arquivo;
   - linha ou trecho aproximado;
   - descrição;
   - impacto;
   - recomendação.
6. Não invente problemas que não estejam presentes no código.
7. Não modifique nenhum arquivo durante as Fases 1 e 2.
8. A Fase 2 deve obrigatoriamente terminar solicitando confirmação do usuário.
9. Somente execute a Fase 3 se o usuário confirmar explicitamente.
10. Preserve o comportamento e os endpoints existentes durante a refatoração.
11. Após a refatoração, valide que a aplicação continua funcionando.

---

# Arquivos de Referência

Antes de executar cada fase, consulte os arquivos apropriados:

- `project-analysis.md`
  - heurísticas para identificação de linguagem, framework, banco e arquitetura.

- `anti-patterns.md`
  - catálogo de code smells e anti-patterns com severidades e sinais de detecção.

- `report-template.md`
  - formato obrigatório do relatório da auditoria.

- `mvc-guidelines.md`
  - estrutura MVC esperada após a refatoração.

- `refactoring-playbook.md`
  - estratégias de transformação e exemplos antes/depois.

---

# PHASE 1 — ANALYSIS

Objetivo: entender completamente o projeto antes da auditoria.

Consulte `project-analysis.md`.

Analise:

- arquivos e diretórios;
- extensões predominantes;
- arquivos de dependências;
- linguagem;
- framework;
- banco de dados;
- ORM ou biblioteca de persistência;
- entry point;
- rotas/endpoints;
- Models;
- Controllers;
- Services;
- configuração;
- utilitários;
- testes;
- arquitetura atual.

Não modifique arquivos nesta fase.

Ao terminar, apresente:

## Project Analysis

- Language:
- Framework:
- Database:
- ORM / Database Library:
- Application Type:
- Entry Point:
- Current Architecture:
- Main Directories:
- Main Architectural Problems:

Em seguida, continue automaticamente para a Fase 2.

---

# PHASE 2 — ARCHITECTURAL AUDIT

Objetivo: identificar problemas reais existentes no projeto.

Consulte:

- `anti-patterns.md`
- `report-template.md`

Analise todos os arquivos relevantes do projeto e compare o código
com o catálogo de anti-patterns.

Procure especialmente por:

- credenciais hardcoded;
- informações sensíveis expostas;
- SQL Injection;
- execução arbitrária de SQL;
- criptografia insegura;
- God Classes;
- God Methods;
- responsabilidades excessivas;
- lógica de negócio em Routes ou Controllers;
- acesso direto ao banco em camadas inadequadas;
- estado global mutável;
- alto acoplamento;
- ausência de separação de responsabilidades;
- N+1 Queries;
- duplicação;
- tratamento inconsistente de erros;
- ausência de validação;
- APIs deprecated;
- magic numbers;
- magic strings;
- nomes pouco descritivos;
- imports ou código não utilizados.

Para cada finding, classifique a severidade como:

- CRITICAL
- HIGH
- MEDIUM
- LOW

Não classifique um problema apenas pelo nome.
Considere o contexto e impacto real no projeto.

Exemplos:

- SQL parametrizado não deve ser reportado como SQL Injection.
- Uma query SQL fixa não deve ser reportada como SQL Injection.
- Um loop comum não deve ser reportado como N+1.
- N+1 exige consultas adicionais executadas repetidamente durante iterações.
- Um valor de configuração não é necessariamente uma credencial.
- APIs deprecated devem ser identificadas somente quando houver evidência de depreciação ou uso de API legada conhecida.

Encontre no mínimo 5 findings.

O relatório deve conter pelo menos um finding CRITICAL ou HIGH quando
houver problema dessa severidade no projeto.

Gere o relatório seguindo `report-template.md`.

---

# STOP POINT — CONFIRMAÇÃO OBRIGATÓRIA

Após apresentar o relatório da Fase 2:

NÃO modifique nenhum arquivo.

Mostre obrigatoriamente:

`Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`

Aguarde a resposta do usuário.

Se a resposta for negativa, encerre a execução sem alterar arquivos.

Se a resposta for positiva, prossiga para a Fase 3.

---

# PHASE 3 — REFACTORING

Objetivo: corrigir os problemas encontrados preservando o comportamento existente.

Antes de modificar arquivos, consulte:

- `mvc-guidelines.md`
- `refactoring-playbook.md`

Crie um plano de refatoração baseado exclusivamente nos findings encontrados.

A arquitetura alvo deve separar, quando aplicável:

- Models;
- Views ou Routes;
- Controllers;
- Services;
- configuração;
- acesso a dados;
- middlewares;
- tratamento de erros;
- entry point / composition root.

A adaptação deve respeitar a linguagem e o framework detectados.

Não force estruturas específicas de Python em Node.js nem estruturas
específicas de Node.js em Python.

Corrija os findings identificados sempre que possível.

Durante a refatoração:

1. Preserve os endpoints existentes.
2. Preserve contratos de entrada e saída quando possível.
3. Extraia configurações sensíveis do código.
4. Utilize queries parametrizadas quando houver SQL dinâmico.
5. Separe lógica de negócio de rotas/controllers.
6. Reduza duplicação.
7. Elimine estado global mutável quando apropriado.
8. Centralize tratamento de erros quando suportado pela tecnologia.
9. Substitua APIs deprecated por alternativas atuais.
10. Preserve compatibilidade com as dependências existentes sempre que possível.

---

# VALIDATION

Depois da refatoração, valide obrigatoriamente o projeto.

Verifique:

1. dependências;
2. imports;
3. sintaxe;
4. inicialização da aplicação;
5. rotas/endpoints existentes;
6. operações principais;
7. conexão com banco;
8. ausência de erros de boot.

Execute os comandos adequados à stack detectada.

Exemplos possíveis:

Python:

```bash
python app.py