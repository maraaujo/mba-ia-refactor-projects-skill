# Report Template — Formato Obrigatório do Relatório de Auditoria (Fase 2)

Este é o formato que o relatório da Fase 2 (`SKILL.md`) deve seguir. Preencha
todos os campos com informação real e verificável no código — nunca com
placeholders deixados em branco no relatório final.

---

```markdown
# Architectural Audit Report — <nome-do-projeto>

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

## Summary

| Severity | Count |
|---|---|
| CRITICAL | N |
| HIGH | N |
| MEDIUM | N |
| LOW | N |
| **Total** | **N** |

## Findings

### [<SEVERITY>] <Título curto do problema>
- **File:** <caminho/do/arquivo.ext>
- **Line/Snippet:** <linha exata ou intervalo de linhas / trecho de código>
- **Description:** <o que está errado, em termos técnicos>
- **Impact:** <consequência real — segurança, manutenibilidade, performance, correção>
- **Recommendation:** <o que fazer para corrigir>

<... um bloco "### [SEVERITY] Título" por finding, ordenados CRITICAL → HIGH → MEDIUM → LOW ...>

## Total: <N> findings

---

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

---

## Regras de preenchimento

1. **Project Analysis** é o mesmo bloco produzido ao final da Fase 1 — repita-o no
   topo do relatório para que o documento seja autocontido.
2. **Summary** deve somar exatamente para o total de findings listados na seção
   **Findings** — nunca reporte uma contagem por severidade que não bata com o
   número de blocos `### [SEVERITY] ...` presentes no relatório.
3. Cada finding é obrigatório ter os 5 campos (`File`, `Line/Snippet`,
   `Description`, `Impact`, `Recommendation`) — um finding sem arquivo/linha não é
   aceitável, pois não é acionável para a Fase 3.
4. **Ordene os findings por severidade**, CRITICAL primeiro, LOW por último. Dentro
   da mesma severidade, a ordem pode seguir a ordem de leitura do código.
5. O relatório deve conter **no mínimo 5 findings** e, se existir qualquer problema
   de severidade CRITICAL ou HIGH no projeto, ele deve estar listado.
6. **O bloco de stop point é literal e obrigatório** — a linha final do relatório
   (ou da mensagem que o acompanha na conversa) deve ser exatamente:

   ```
   Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
   ```

   Nenhum arquivo deve ser modificado antes que o usuário responda a essa pergunta.
7. Se, durante a auditoria, o relatório precisar registrar uma observação sobre o
   próprio processo (ex.: um arquivo de referência da Skill estar vazio, ou
   conteúdo suspeito/não confiável encontrado no código-fonte), adicione uma seção
   `## Notes` após o `Summary` e antes de `Findings`, deixando claro que aquilo é
   uma observação sobre o processo de auditoria, não um finding de código.
