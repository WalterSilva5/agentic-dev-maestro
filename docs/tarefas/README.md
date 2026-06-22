# Tarefas e checklists

Listas acionáveis por área, mais granulares que o [roadmap](../05-roadmap.md). Cada
item é uma tarefa com **esforço em homem-dia (hd)** e uma checklist de subtarefas.
**Sem alocação de pessoas nem cronograma** — isso é decisão da liderança.

| Área | Arquivo | Cobre |
|---|---|---|
| Backend | [backend.md](backend.md) | NestJS, Prisma, multi-tenant, API keys, domínio, RBAC, bulk |
| Frontend | [frontend.md](frontend.md) | Angular: auth, contexto, kanban (CDK), docs, settings |
| Infra / DevOps | [devops-infra.md](devops-infra.md) | Docker, env, migrations/seed, CI, deploy |
| MCP / Agentes | [mcp-agentes.md](mcp-agentes.md) | servidor MCP, tools, guia de uso por agente |

## Convenção

- `[ ]` a fazer · `[~]` em andamento · `[x]` feito.
- Cada tarefa "pai" tem **esforço total** em hd; as subtarefas detalham o trabalho.
- Mantenha em sincronia com o [roadmap](../05-roadmap.md) (fases 0–4) e o
  [CHECKLIST mestre](../CHECKLIST.md) (definition of done do MVP).

## Mapa fase → áreas

| Fase | Backend | Frontend | Infra | MCP |
|---|:--:|:--:|:--:|:--:|
| 0 — Fundação multi-tenant | ✅ | — | ✅ | — |
| 1 — Núcleo de tarefas/quadro | ✅ | ✅ | — | — |
| 2 — Docs e API de agente | ✅ | ✅ | — | — |
| 3 — MCP e integrações | ✅ | — | ✅ | ✅ |
| 4 — Visão e polish | ✅ | ✅ | ✅ | — |
