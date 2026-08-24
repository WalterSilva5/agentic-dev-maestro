---
name: maestro-use
description: Analyze the current chat and Maestro workspace state, then pick and start the right Maestro skills (board, memory, daily, review). Use when the user runs /maestro-use, asks what to do in Maestro now, or after many chat actions needs a workflow reset.
---

# maestro-use — Orquestrador de skills Maestro

Mini skill de **roteamento**. Decide quais skills Maestro usar **agora** e executa o primeiro passo útil.

API: `http://127.0.0.1:9777/api` · Tools: `maestro_*`

## Snapshot (obrigatório, paralelo)

```bash
curl -s http://127.0.0.1:9777/api/health
curl -s http://127.0.0.1:9777/api/projects
curl -s 'http://127.0.0.1:9777/api/activity?limit=15'
curl -s http://127.0.0.1:9777/api/daily/$(date +%F)
curl -s -X POST http://127.0.0.1:9777/api/memory/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"contexto da sessão decisões preferências","topK":5}'
```

Offline → `maestro-run` e pare. Senão use também `maestro_listProjects`, `maestro_board`, `maestro_searchMemory`.

## Momentos

| Momento | Sinais |
|---------|--------|
| `boot` | sessão nova, continuar, onde paramos |
| `planejar` | sprint, priorizar, backlog |
| `executar` | codando feature/bug |
| `revisar` | review, PR, coluna Revisão |
| `documentar` | ADR, spec |
| `memorizar` | "lembra", preferência, lição |
| `diario` | standup, fim do dia |
| `setup` | projeto novo |
| `incidente` | bug urgente / prod |

## Mapa skill → momento

| Skill | Quando |
|-------|--------|
| `maestro-context-loader` | boot |
| `maestro-agentic-memory` | boot / memorizar / após decisão |
| `maestro-task-workflow` | executar |
| `maestro-code-review-log` | revisar |
| `maestro-bug-triage` | incidente |
| `maestro-sprint-planning` | planejar |
| `maestro-daily-standup` / `maestro-daily-report` | diário |
| `maestro-project-setup` | setup |
| `maestro-documentation-writer` | documentar |
| `maestro-tech-debt-tracker` | dívida técnica |
| `maestro-api-agent` | qualquer REST |
| `maestro-run` | API down |

Máx. **3 skills**. Preferir ação a catálogo.

## Resposta

```markdown
## Momento
- Primário / secundários / evidências

## Skills agora
1. **id** — por quê

## Próximas ações
1. …

## Já faço agora
(executar 1ª ação)
```

## Ação imediata

- **boot** → context + `maestro_searchMemory`
- **executar** sem task → `maestro_createTask` + move Fazendo
- **decisão** → `maestro_remember` (decision/preference)
- **fim task** → comment + move Revisão
- **fim dia** → daily-report
- **incidente** → bug-triage + URGENT

## Atalhos

continuar→context+memory+Fazendo · o que fazer→board+prefs · review→code-review-log · anota→remember · fechei o dia→daily-report · bug prod→bug-triage · projeto novo→project-setup
