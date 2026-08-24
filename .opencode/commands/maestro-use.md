---
description: Analisa o momento atual e recomenda/executa as skills Maestro adequadas
---

# /maestro-use — Orquestrador de skills do Maestro

Você é o **roteador** do Agentic Dev Maestro. O usuário pediu orientação sobre o que
fazer agora no Maestro (board, memória, diário, skills). Argumentos opcionais: $ARGUMENTS

## Objetivo

1. Entender o **momento** (conversa + estado do workspace + argumentos)
2. Escolher as **skills Maestro** certas
3. **Agir** (ou propor o próximo passo concreto) — não só listar skills

## Passo 0 — Contexto rápido (obrigatório, em paralelo)

```bash
curl -s http://127.0.0.1:9777/api/health
curl -s http://127.0.0.1:9777/api/projects
curl -s 'http://127.0.0.1:9777/api/activity?limit=15'
curl -s http://127.0.0.1:9777/api/daily/$(date +%F)
curl -s -X POST http://127.0.0.1:9777/api/memory/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"'"${ARGUMENTS:-contexto da sessão e decisões recentes}"'","topK":5}'
```

Se a API estiver down: orientar `maestro-run` e parar.

Tools OpenCode úteis em paralelo: `maestro_listProjects`, `maestro_board`,
`maestro_searchMemory`, `maestro_listTasks`.

## Passo 1 — Classificar o momento

Escolha **1 primário** + até **2 secundários**:

| Momento | Sinais |
|---------|--------|
| `boot` | Sessão nova, "continuar", "onde paramos", workspace trocado |
| `planejar` | "sprint", "priorizar", "o que fazer", backlog cheio |
| `executar` | Tarefa em Fazendo, implementação, bug, feature |
| `revisar` | "review", PR, coluna Revisão, code review |
| `documentar` | ADR, spec, "documentar", decisões técnicas |
| `memorizar` | Decisão importante, preferência, lição, "lembre" |
| `diario` | Fim do dia, standup, relatório, "o que fiz" |
| `setup` | Projeto novo, labels, colunas, primeiro uso |
| `incidente` | Bug urgente, produção, hotfix |
| `estudo` | Plano de estudo, aprender tecnologia |

Use também o histórico **desta conversa** (ações já feitas no chat).

## Passo 2 — Mapa skill → momento

| Skill | Quando acionar |
|-------|----------------|
| `maestro-run` | API offline |
| `maestro-context-loader` | `boot` — sempre no início de sessão |
| `maestro-agentic-memory` | `boot`, `memorizar`, `documentar`, `executar` (buscar antes / gravar depois) |
| `maestro-api-agent` | Qualquer fluxo via REST/tools |
| `maestro-task-workflow` | `executar` — ciclo criar→fazer→revisar→concluir |
| `maestro-project-setup` | `setup` |
| `maestro-sprint-planning` | `planejar` com sprints |
| `maestro-code-review-log` | `revisar` |
| `maestro-bug-triage` | `incidente` / bug |
| `maestro-daily-standup` | manhã / `diario` leve |
| `maestro-daily-report` | fim do dia / `diario` completo |
| `maestro-tech-debt-tracker` | dívida técnica, refactor |
| `maestro-documentation-writer` | `documentar` |
| `maestro-use` (esta) | meta: reavaliar o que fazer agora |

## Passo 3 — Resposta obrigatória (formato)

Responda em português, curto:

```markdown
## Momento
- Primário: …
- Secundários: …
- Evidências: (1–3 bullets do board/atividade/chat)

## Skills agora
1. **skill-id** — por quê (1 linha)
2. …

## Próximas ações (executar nesta ordem)
1. …
2. …

## Já faço agora
(execute a 1ª ação útil: search memory, mover task, criar task, comentário, etc.)
```

## Passo 4 — Executar (não só recomendar)

Salvo se o usuário pediu "só orientar":

- `boot` → rode o essencial do `maestro-context-loader` + `maestro_searchMemory`
- `executar` sem tarefa → `maestro_createTask` + mover para Fazendo
- decisão na conversa → `maestro_remember` (kind=decision|preference)
- fim de trabalho em task → comentário + move para Revisão
- fim de dia → esboçar `maestro-daily-report`

## Regras

- Máximo **3 skills** recomendadas por vez
- Prefira **ação** a catálogo genérico
- Respeite `requiresHuman` — não "conclua" sozinho o que é do dev
- Não invente projectId/task codes — leia da API
- Se `$ARGUMENTS` trouxer foco (ex: "review DEMO-3"), priorize isso
- Se incerto entre 2 caminhos, escolha o de **menor risco** e diga a alternativa

## Atalhos por frase do usuário

- "continuar" / "onde paramos" → context-loader + memory search + board Fazendo
- "o que fazer" / "priorizar" → board + metrics + memory preferences
- "review" → code-review-log + getTask/getFlow
- "lembra que…" / "anota" → agentic-memory remember
- "fechei o dia" → daily-report
- "bug em prod" → bug-triage + task URGENT
- "projeto novo" → project-setup
