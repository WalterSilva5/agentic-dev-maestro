> 🇧🇷 [Versão em português](README.ptbr.md)

# Tasks and checklists

> **Status (2026-06-22):** these lists are the **execution plan** (with effort in md).
> Phases 0–2 are fully implemented and 3–4 with caveats — the **actual status
> and open items** are in the [master CHECKLIST](../CHECKLIST.md), the single source of truth.

Actionable lists by area, more granular than the [roadmap](../05-roadmap.md). Each
item is a task with **effort in man-days (md)** and a checklist of subtasks.
**No people allocation or schedule** — that is a leadership decision.

| Area | File | Covers |
|---|---|---|
| Backend | [backend.md](backend.md) | NestJS, Prisma, multi-tenant, API keys, domain, RBAC, bulk |
| Frontend | [frontend.md](frontend.md) | Angular: auth, context, kanban (native HTML5 DnD), docs, settings |
| Infra / DevOps | [devops-infra.md](devops-infra.md) | Docker, env, migrations/seed, CI, deploy |
| MCP / Agents | [mcp-agentes.md](mcp-agentes.md) | MCP server, tools, per-agent usage guide |

## Convention

- `[ ]` to do · `[~]` in progress · `[x]` done.
- Each "parent" task has a **total effort** in md; the subtasks detail the work.
- Keep in sync with the [roadmap](../05-roadmap.md) (phases 0–4) and the
  [master CHECKLIST](../CHECKLIST.md) (MVP definition of done).

## Phase → areas map

| Phase | Backend | Frontend | Infra | MCP |
|---|:--:|:--:|:--:|:--:|
| 0 — Multi-tenant foundation | ✅ | — | ✅ | — |
| 1 — Task/board core | ✅ | ✅ | — | — |
| 2 — Docs and agent API | ✅ | ✅ | — | — |
| 3 — MCP and integrations | ✅ | — | ✅ | ✅ |
| 4 — Vision and polish | ✅ | ✅ | ✅ | — |
