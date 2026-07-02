> 🇧🇷 [Versão em português](backend.ptbr.md)

# Tasks — Backend (NestJS + Prisma)

Base: `fullstack-nestjs-angular` template (auth, users, roles, Prisma/MySQL,
Bull/Redis, Swagger already in place). Effort in man-days (md).

---

## Phase 0 — Multi-tenant foundation

### B0.1 — Project setup from the template · 0.5 md
- [ ] Copy the template's `back/` into the `maestro` project
- [ ] Rename app/package, adjust `.env.example` (DB, JWT, REDIS)
- [ ] Bring it up with Docker (`docker compose up`) and validate `/api/docs` (Swagger)

### B0.2 — Company and Membership models · 1.5 md
- [ ] Add `Company`, `Membership`, `Role` enum to `schema.prisma`
- [ ] `User ↔ Membership ↔ Company` relationship (`@@unique([userId, companyId])`)
- [ ] Migration + `prisma generate`
- [ ] `companies` and `memberships` modules (basic CRUD)

### B0.3 — Multi-tenant context guard · 1.5 md
- [ ] Resolve `companyId` from the JWT (`X-Company-Id`) or from the API key
- [ ] Load the `Membership` and expose the role in the request context
- [ ] **Row-level filter**: helper/decorator that injects `companyId` into every query
- [ ] Block cross-company access (isolation test)

### B0.4 — API key authentication · 2 md
- [ ] `ApiKey` model (hash, prefix, scopes, expiresAt, revokedAt) + migration
- [ ] Generation: create the key, return the secret **once**, store only the hash
- [ ] `x-api-key` guard → resolves `Membership` + `scopes`
- [ ] Endpoints: list / create / revoke (`apikeys:manage` scope)
- [ ] Rate limit per key + `lastUsedAt` update

### B0.5 — Initial seed · 0.5 md
- [ ] Demo company + OWNER user + 1 agent API key (DEV role)

---

## Phase 1 — Task and board core

### B1.1 — Projects · 1.5 md
- [ ] `Project` model (`key`, `@@unique([companyId, key])`) + migration
- [ ] Project CRUD (`projects:*` scope)
- [ ] On project creation, create a default `Board` + default columns

### B1.2 — Board, columns and ordering · 1.5 md
- [ ] `Board`, `Column` (order, wipLimit) models + migration
- [ ] Endpoints: read full board, create/rename/reorder column
- [ ] Lexicographic `rank` strategy (insertion/move helper)

### B1.3 — Tasks and subtasks · 3 md
- [ ] `Task` model (sequential number, parentId, estimateMd, priority, rank, **objective**, **acceptance**)
- [ ] Task CRUD; `number` generation → `GAV-42` code
- [ ] Accept `idOrCode` in the routes (`/tasks/GAV-42`)
- [ ] Subtasks (self-relational)
- [ ] `POST /tasks/:code/move` (changes column + rank) with WIP validation

### B1.6 — Dependencies and task flow (DAG) · 2.5 md
> Feature from [doc 08](../08-fluxo-de-tarefas.md).
- [ ] `TaskDependency` model (blocker → blocked) + migration; `@@unique`
- [ ] `POST /tasks/:code/dependencies` with **cycle validation** (DFS) + same `companyId`
- [ ] `DELETE /tasks/:code/dependencies/:depId`
- [ ] `GET /tasks/:code/flow` → `{ nodes, edges }` with synthetic **Objective** and **Acceptance** nodes
- [ ] Derive **blocked** state (blocker not completed) + progress (% of subtasks)
- [ ] `?format=mermaid` → emit `flowchart` for export in the markdown docs
- [ ] In `POST /tasks/bulk`, resolve `dependsOn` (batch refs) → create edges in the transaction

### B1.4 — Labels · 1 md
- [ ] `Label` model per company + N:N relation with `Task`
- [ ] Label endpoints + apply/remove on a task

### B1.5 — Swagger + DTOs + validation · 1 md
- [ ] DTOs with `class-validator` for everything above
- [ ] Swagger tags organized by resource; examples on the agent endpoints

---

## Phase 2 — Docs and agent API

### B2.1 — Markdown documents · 2 md
- [ ] `Document` model (markdown body, type, version) linked to Project/Task
- [ ] CRUD; increment `version` on edit
- [ ] Export endpoint (plain markdown text)

### B2.2 — Bulk create (decompose) · 1.5 md
- [ ] `POST /tasks/bulk` accepts an array with nested subtasks
- [ ] Creation within a **transaction** (all or nothing)
- [ ] Returns the generated codes (`GAV-1..n`)

### B2.3 — Idempotency · 1 md
- [ ] `Idempotency-Key` header on creations (docs and tasks)
- [ ] Table/cache of processed keys (TTL) → resend does not duplicate

### B2.4 — Auditing · 1.5 md
- [ ] `ActivityLog` model (actorUserId, viaApiKeyId, action, changes)
- [ ] Interceptor/service that records every write (human vs. agent)
- [ ] Endpoint to read activity (by task/project)

---

## Phase 3/4 — RBAC, integrations and polish

### B3.1 — Declarative RBAC · 1.5 md
- [ ] `@RequireScope(...)` / `@RequireRole(...)` decorator
- [ ] Guard that applies **effective permission = role ∩ scopes** (see matrix in doc 04)
- [ ] Tests for the per-role permission matrix

### B3.2 — Webhooks and notifications · 2.5 md
- [ ] Bull queue: status-change event → triggers the company's webhook(s)
- [ ] Notification email reusing the template's queue
- [ ] Per-company webhook config (URL, HMAC secret)

### B4.1 — Search and filters · 2 md
- [ ] `GET /tasks` with filters (status, assignee, label, priority, text)
- [ ] Pagination and ordering

### B4.2 — Invitations and member management · 1.5 md
- [ ] Invite a user to a company (by email) + accept
- [ ] Change role / remove member (respecting OWNER rules)

---

## Quality checklist (backend)

- [ ] Multi-tenant isolation tested (no query without `companyId`)
- [ ] API key: only the hash in the database; secret shown once; immediate revocation works
- [ ] Every write generates an `ActivityLog` with the correct actor
- [ ] Bulk + idempotency tested against duplication
- [ ] Permission matrix covered by tests
- [ ] Swagger complete and up to date (`/api/docs`)
- [ ] Versioned migrations; reproducible seed
