---
name: relay-use
description: Analyze the current moment and pick the right Relay skills to run now. Trigger with /relay-use or when unsure what to do next in Relay.
---

# relay-use — Orquestrador de skills

Mini skill de **roteamento**. Nao substitui as outras skills: decide **quais**
usar agora com base na conversa + estado do workspace, e executa o primeiro passo.

Base API: `http://127.0.0.1:9777/api`

## QUANDO USAR

- Inicio de sessao ou "o que faco agora no Relay?"
- Depois de varias acoes no chat e precisar reorganizar o fluxo
- Quando o agente estiver perdido entre board / memoria / diario / review
- Comando OpenCode: `/relay-use [foco opcional]`

## PASSO 0 — Snapshot (paralelo, obrigatorio)

```bash
curl -s http://127.0.0.1:9777/api/health | jq .
curl -s http://127.0.0.1:9777/api/projects | jq '.[] | {id,key,name}'
curl -s 'http://127.0.0.1:9777/api/activity?limit=15' | jq '.[:10]'
curl -s http://127.0.0.1:9777/api/daily/$(date +%F) | jq '{notes, report}'
curl -s -X POST http://127.0.0.1:9777/api/memory/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"contexto da sessao decisoes preferencias","topK":5}' \
  | jq '{count, agentContext}'
```

API offline → so `relay-run`. Pare.

## PASSO 1 — Classificar o momento (1 primario + ate 2 secundarios)

| Momento | Sinais |
|---------|--------|
| `boot` | sessao nova, continuar, onde paramos |
| `planejar` | sprint, priorizar, backlog |
| `executar` | feature/bug em andamento, codando |
| `revisar` | review, PR, coluna Revisao |
| `documentar` | ADR, spec, documentar decisao |
| `memorizar` | "lembra", preferencia, licao |
| `diario` | standup, fim do dia, relatorio |
| `setup` | projeto novo, labels, primeiro uso |
| `lideranca` | goals, metricas por pessoa, acompanhamento |
| `incidente` | bug urgente, hotfix, prod |
| `estudo` | aprender, plano de estudo |

Leia tambem o historico **desta conversa**.

## PASSO 2 — Mapa skill → momento

| Skill | Momentos |
|-------|----------|
| `relay-run` | API down |
| `relay-context-loader` | boot |
| `relay-agentic-memory` | boot, memorizar, documentar, executar |
| `relay-api-agent` | qualquer fluxo REST |
| `relay-task-workflow` | executar |
| `relay-project-setup` | setup |
| `relay-goals` | lideranca, planejar |
| `relay-members` | lideranca, executar |
| `relay-sprint-planning` | planejar |
| `relay-code-review-log` | revisar |
| `relay-bug-triage` | incidente |
| `relay-daily-standup` | diario (manha) |
| `relay-daily-report` | diario (fim do dia) |
| `relay-tech-debt-tracker` | divida tecnica |
| `relay-documentation-writer` | documentar |
| `relay-use` | reavaliar o roteamento |

## PASSO 3 — Formato da resposta

```markdown
## Momento
- Primario: …
- Secundarios: …
- Evidencias: …

## Skills agora
1. **id** — por que
2. …

## Proximas acoes
1. …
2. …

## Ja faco agora
(executar a 1a acao util)
```

Maximo **3 skills**. Prefira acao a catalogo.

## PASSO 4 — Executar o primeiro passo

| Momento | Acao imediata |
|---------|----------------|
| boot | context-loader essencial + memory search |
| executar (sem task) | criar task + mover para Fazendo |
| decisao na conversa | POST /api/memory (kind=decision) |
| fim de task | comentario + move Revisao |
| fim do dia | daily-report |
| incidente | bug-triage + task URGENT |

## Atalhos de frase

- "continuar" → context-loader + memory + board Fazendo
- "o que fazer" → board + metrics + preferences na memory
- "review" → code-review-log
- "anota/lembra" → agentic-memory remember
- "fechei o dia" → daily-report
- "bug em prod" → bug-triage
- "projeto novo" → project-setup
- "goal" ou "progresso" → relay-goals
- "quem faz" ou "responsavel" → relay-members

## Regras

- Nao inventar projectId/codes — ler da API
- Respeitar `requiresHuman`
- Se incerto, caminho de menor risco + alternativa em 1 linha
- OpenCode: tools `relay_*` + comando `/relay-use`
