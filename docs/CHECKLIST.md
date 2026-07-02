> 🇧🇷 [Versão em português](CHECKLIST.ptbr.md)

# Master checklist — Definition of Done

A single view of what needs to be ready. State as of 2026-06-25.

> Convention: `[ ]` to do · `[~]` partial · `[x]` done.

---

## 🚪 Gate 0 — Multi-tenant foundation ✅

- [x] Project from the template; `docker compose` brings up mysql/redis/api/front
- [x] `Company` + `Membership` + roles (OWNER/MANAGER/TECH_LEAD/DEV/VIEWER)
- [x] Context guard + **isolation by `companyId`**
- [x] Authentication via **API key** (sha256 hash, scopes, expiration, revocation)
- [x] Seed: demo company + OWNER + agent API key

## 🚪 Gate 1 — Task and board core ✅

- [x] Projects with `key` and automatic default board (5 columns)
- [x] Board with configurable columns + lexicographic `rank`
- [x] Tasks with code (`DEMO-42`), priority, estimate (person-days), labels
- [x] Tasks with **objective** and **acceptance criterion**
- [x] Subtasks (self-relational)
- [x] `move` (change column/status) — done
- [x] **Task flow:** `TaskDependency` (validated DAG, anti-cycle) + `GET /flow`
- [x] **Front:** kanban with drag-and-drop, optimistic update + rollback
- [x] **Front:** task detail (objective, acceptance, comments; subtasks via flow)
- [x] **Front:** flow tab with nodes by status + Mermaid export

## 🚪 Gate 2 — Docs and agent API → functional MVP ✅

- [x] `Document` markdown (version) on project/task + export
- [x] `POST /tasks/bulk` (decompose) in a transaction, with `dependsOn`
- [x] Idempotency (`Idempotency-Key`) without duplication
- [x] `ActivityLog` on every write (human vs. agent)
- [x] **Front:** markdown editor/viewer (textarea) + activity tab

## 🚪 Gate 3 — MCP and integrations ✅

- [x] MCP server (`mcp/`) with 11 tools
- [x] Status webhooks (HMAC dispatch on `task.created/moved`)

## 🚪 Gate 4 — Overview and polish ✅

- [x] Search + filters on `GET /tasks`
- [x] Dashboard (progress per project + recent activity)
- [x] Member and API key management in the UI
- [x] Navigation links (navbar) to the Maestro pages

## 🚪 Gate 5 — Studies Module ✅

- [x] SQLAlchemy models: StudyPlan, StudyTopic, StudySession
- [x] CRUD endpoints for plans, topics and sessions
- [x] Automatic progress calculation
- [x] GUI with a list of plans, detail with topics
- [x] "Studies" sidebar in the local-client

## 🚪 Gate 6 — Task Editing/Deletion ✅

- [x] Backend: `PATCH /tasks/:code` (update), `DELETE /tasks/:code` (soft delete)
- [x] Backend: `PATCH /comments/:id` (update), `DELETE /comments/:id` (delete)
- [x] Backend: `parentId` filter on `GET /tasks`
- [x] Frontend: Clickable cards on the board → open details
- [x] Frontend: Inline edit form in the task detail
- [x] Frontend: Subtasks tab (create/delete, title only)
- [x] Frontend: Inline comment editing/deletion
- [x] Frontend: Column selector to move a task
- [x] Frontend: Highlighted description card

## 🚪 Gate 7 — OpenCode Tools ✅

- [x] 12 custom tools (`.opencode/tools/maestro.ts`)
- [x] 2 commands: `/review` and `/decompose`
- [x] Platform usage skill
- [x] `opencode.jsonc` config

## 🚪 Gate 8 — Reorganization ✅

- [x] Web client moved to `web-client/`
- [x] General README + web client README
- [x] CLAUDE.md updated with new paths
- [x] Light theme with better contrast (white cards, visible borders)
- [x] Sidebar without unnecessary scroll
- [x] Board view shows a list of projects when none is selected

---

## Known pending items (next steps)

1. Real timer for study sessions
2. Gamification (streak, badges, XP)
3. Roadmap import in markdown
4. Flashcards/spaced repetition
5. Sharing plans as templates
6. CI (lint + test + build) — not configured
7. Automated tests (RBAC, isolation)
