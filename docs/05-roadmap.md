> 🇧🇷 [Versão em português](05-roadmap.ptbr.md)

# 05 — Roadmap

> **State (2026-06-22):** Phases **0–2 (MVP)** are implemented and verified, and
> Phases **3–4** implemented with caveats. The `[ ]` checkboxes below are the
> **original plan** (for sizing); the **actual state and pending items** live
> in [CHECKLIST.md](CHECKLIST.md) — the single source of truth for status.

Effort in **person-days (pd)**, in ranges. **There is no allocation of people nor
a schedule** — leadership distributes the work and sets deadlines. The ranges
serve only to size each block.

> Baseline: the `fullstack-nestjs-angular` template already delivers auth, users, roles
> (USER/ADMIN/MANAGER), Prisma+MySQL, Bull/Redis, Swagger and Docker. The estimates
> below assume that starting point.

---

## Phase 0 — Multi-tenant foundation · ~5–8 pd

Extend the template to the domain of companies and agents.

- [ ] `Company` and `Membership` models + Prisma migration — **1–2 pd**
- [ ] Adapt roles: new `Role` enum (OWNER/MANAGER/TECH_LEAD/DEV/VIEWER) on the Membership — **1 pd**
- [ ] Company context guard + row-level filter by `companyId` — **1–2 pd**
- [ ] `ApiKey` model + auth via `x-api-key` (hash, scopes, revocation) — **2 pd**
- [ ] Seed: demo company + owner + agent key — **0.5 pd**

## Phase 1 — Task and board core · ~12–18 pd

The heart of the product.

- [ ] `Project`, `Board`, `Column`, `Task` models (+ subtasks) + migration — **2 pd**
- [ ] Project CRUD + board creation with default columns — **1.5 pd**
- [ ] Task CRUD: create, edit, assign, priority, estimate (pd), tags — **2–3 pd**
- [ ] `move` endpoint (change column/status + rank/ordering) — **1 pd**
- [ ] Subtasks (self-relational) — **1 pd**
- [ ] **Front:** kanban board screen with drag-and-drop — **3–5 pd**
- [ ] **Front:** task panel/modal (detail, editing, subtasks) — **2–3 pd**
- [ ] **Front:** project list + creation — **1.5 pd**

## Phase 2 — Docs and agent API · ~8–12 pd

Where the differentiator appears.

- [ ] `Document` model (markdown, version) on project/task + CRUD — **2 pd**
- [ ] **Front:** markdown editor/viewer + `.md` export — **2–3 pd**
- [ ] `POST /tasks/bulk` (decompose: tasks + subtasks in a transaction) — **1.5 pd**
- [ ] Idempotency (`Idempotency-Key`) on creations — **1 pd**
- [ ] `ActivityLog` + automatic recording on writes (human vs. agent) — **1.5 pd**
- [ ] **Front:** activity/audit tab on the task and the project — **1.5 pd**

**🎯 Functional MVP at the end of Phase 2** (~25–38 pd accumulated): the full loop
— briefing → doc → tasks → board → agent execution — runs end to end.

## Phase 3 — MCP server and integrations · ~6–10 pd

- [ ] MCP server package wrapping the API — **3–4 pd**
- [ ] MCP tools: `decompose`, `write_doc`, `list_tasks`, `move_task`, `comment` — **2–3 pd**
- [ ] Status-change webhooks (Bull queue) — **1.5 pd**
- [ ] Email notifications (reuses the template's queue) — **1 pd**

## Phase 4 — View and polish · ~6–10 pd

- [ ] Search + advanced filters (assignee, label, status, text) — **2 pd**
- [ ] Labels per company — **1 pd**
- [ ] Manager dashboard (progress per project/company) — **2–3 pd**
- [ ] Member and API key management in the UI — **2 pd**
- [ ] User invitations to a company — **1.5 pd**

---

## Effort summary

| Phase | Focus | Effort |
|---|---|---|
| 0 | Multi-tenant foundation | ~5–8 pd |
| 1 | Task and board core | ~12–18 pd |
| 2 | Docs and agent API | ~8–12 pd |
| **—** | **Functional MVP (0→2)** | **~25–38 pd** |
| 3 | MCP and integrations | ~6–10 pd |
| 4 | View and polish | ~6–10 pd |
| **—** | **Complete product (0→4)** | **~37–58 pd** |

## Suggested delivery slicing

1. **Vertical slice first:** one company, one project, one board, create/move a
   task via API with a key — proves the concept end to end before the rich UI.
2. **Then** the kanban UI, **then** docs/bulk/auditing, **finally** MCP and polish.
