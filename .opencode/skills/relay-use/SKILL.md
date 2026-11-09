---
name: relay-use
description: Analyze the current chat and Relay workspace state, then pick and start the right Relay skills (board, memory, daily, review). Use when the user runs /relay-use, asks what to do in Relay now, or after many chat actions needs a workflow reset.
---

# relay-use — Orquestrador de skills Relay

Mini skill de **roteamento**. Decide quais skills Relay usar **agora** e executa o primeiro passo útil.

API: `http://127.0.0.1:9777/api` · Tools: `relay_*`

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

Offline → `relay-run` e pare. Senão use também `relay_listProjects`, `relay_board`, `relay_searchMemory`.

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
| `relay-context-loader` | boot |
| `relay-agentic-memory` | boot / memorizar / após decisão |
| `relay-task-workflow` | executar |
| `relay-code-review-log` | revisar |
| `relay-bug-triage` | incidente |
| `relay-sprint-planning` | planejar |
| `relay-daily-standup` / `relay-daily-report` | diário |
| `relay-project-setup` | setup |
| `relay-documentation-writer` | documentar |
| `relay-tech-debt-tracker` | dívida técnica |
| `relay-api-agent` | qualquer REST |
| `relay-run` | API down |

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

- **boot** → context + `relay_searchMemory`
- **executar** sem task → `relay_createTask` + move Fazendo
- **decisão** → `relay_remember` (decision/preference)
- **fim task** → comment + move Revisão
- **fim dia** → daily-report
- **incidente** → bug-triage + URGENT

## Atalhos

continuar→context+memory+Fazendo · o que fazer→board+prefs · review→code-review-log · anota→remember · fechei o dia→daily-report · bug prod→bug-triage · projeto novo→project-setup
