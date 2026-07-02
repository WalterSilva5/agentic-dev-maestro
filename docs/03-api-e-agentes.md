> 🇧🇷 [Versão em português](03-api-e-agentes.ptbr.md)

# 03 — API and agents

> Status: **implemented**. This document reflects the real API (NestJS + Swagger).
> Swagger UI: `http://<host>:<port>/api/docs`. All routes are under the global
> prefix **`/api`**.

The API is REST. Two authentication mechanisms:

- **Humans** → JWT (`Authorization: Bearer <accessToken>`) **+ `X-Company-Id` header**
  to choose the active company (multi-tenant).
- **Agents** → **API key** in the **`x-api-key: adm_…`** header. The tenant is resolved
  automatically from the key's *Membership* — the agent does **not** send
  `X-Company-Id`.

The API key is linked to a **Membership** (user + company). The agent inherits the
permissions of that role. The key also stores a list of `scopes` (see below).

## Principles for an agent-friendly API

1. **Bulk for everything that matters** — the *decompose* step creates many tasks at once.
   `POST /api/tasks/bulk` accepts `{ projectId, items[] }` (with nested subtasks and
   dependencies) and creates everything in a single transaction.
2. **Idempotency** — `Idempotency-Key` header on bulk creations; if the agent
   resends after a timeout, it doesn't duplicate tasks. *(Without the key, resends create
   duplicate batches — always send one.)*
3. **Readable codes** — task endpoints accept both a numeric `id` and the
   code (`MAESTRO-4`).
4. **Descriptive errors** — messages in `messages[]` that an agent can
   interpret (missing field, nonexistent project, dependency cycle, etc.).
5. **Built-in flow** — the decompose's `dependsOn` already creates the edges of the task's
   graph; `GET /api/tasks/:code/flow` returns nodes/edges + progress.
6. **Automatic auditing** — every write via API key is recorded in the `ActivityLog`.

## Authentication

### Human (JWT + tenant)

```bash
TOKEN=$(curl -s -X POST http://localhost:5099/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@template.com","password":"Admin@123"}' | jq -r .accessToken)

curl http://localhost:5099/api/projects \
  -H "Authorization: Bearer $TOKEN" -H "X-Company-Id: 2"
```

### Create an API key (management → done by the owner/manager, authenticated via JWT)

```bash
curl -X POST http://localhost:5099/api/companies/2/api-keys \
  -H "Authorization: Bearer $TOKEN" -H "X-Company-Id: 2" \
  -H 'Content-Type: application/json' \
  -d '{"label":"claude-code agent","scopes":["tasks:write","tasks:move","docs:write"]}'
# → returns the secret (adm_…) ONCE. Save it; only the hash stays in the database.
```

### Agent (API key)

```bash
KEY="adm_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
curl http://localhost:5099/api/projects -H "x-api-key: $KEY"   # no X-Company-Id
```

## Implemented endpoints

```
# Auth (humans)
POST   /api/auth/login | /refresh | /logout
POST   /api/auth/forgot-password | /reset-password | /change-password

# Companies and members
GET    /api/companies                         # companies of the user/key
POST   /api/companies
GET    /api/companies/:companyId/members
POST   /api/companies/:companyId/members       # invite/link (sends email)
PATCH  /api/companies/:companyId/members/:membershipId   # change role
DELETE /api/companies/:companyId/members/:membershipId

# API keys (OWNER/MANAGER)
GET    /api/companies/:companyId/api-keys
POST   /api/companies/:companyId/api-keys      # creates → secret (adm_…) ONCE
DELETE /api/companies/:companyId/api-keys/:id  # revokes

# Projects and board
GET    /api/projects                           # projects of the active company
POST   /api/projects                           # creates project (+ "Principal" board with 5 columns)
GET    /api/projects/:id/board                 # full board: columns + tasks

# Tasks
GET    /api/tasks?projectId=&columnId=&assigneeId=&parentId=
POST   /api/tasks                              # { projectId, title, objective?, acceptance?, columnId?, priority?, estimateMd?, parentId? }
POST   /api/tasks/bulk                         # decompose: { projectId, items[] }  (Idempotency-Key)
GET    /api/tasks/:idOrCode                    # accepts "MAESTRO-4"
GET    /api/tasks/:idOrCode/flow               # { task, progress, nodes, edges }; ?format=mermaid → { mermaid }
POST   /api/tasks/:idOrCode/move               # { columnId } → changes status/column
POST   /api/tasks/:idOrCode/dependencies       # { blockerCode } (validates DAG; rejects cycle)
DELETE /api/tasks/:idOrCode/dependencies/:depId

# Markdown documents (on project or task)
GET    /api/documents?projectId=&taskId=
POST   /api/documents                          # { title, body, type?, projectId?, taskId? }
GET    /api/documents/:id  |  PUT /api/documents/:id  |  DELETE /api/documents/:id
GET    /api/documents/:id/export               # plain markdown

# Comments, labels, activity, webhooks
GET    /api/comments?taskId=     POST /api/comments        # { taskId, body }
GET    /api/labels   POST /api/labels   DELETE /api/labels/:id
POST   /api/labels/:id/tasks/:taskId   DELETE /api/labels/:id/tasks/:taskId
GET    /api/activity?entityType=&entityId=&limit=
GET/POST/PATCH/DELETE /api/webhooks            # (OWNER/MANAGER)
```

> There is no `PATCH /tasks` (editing individual fields), no `POST /tasks/:id/subtasks`,
> and no column CRUD — subtasks come from `bulk` (the `subtasks` field) and the columns
> come from the default board created together with the project.

## API key scopes

The key stores `scopes` (e.g.: `tasks:write`, `tasks:move`, `docs:write`), exposed
in the request context. **Today the effective authorization is by the Membership role**
(OWNER/MANAGER/...); granular enforcement by `scope` is a planned refinement.
Suggested vocabulary:

```
companies:read   projects:read   projects:write
tasks:read   tasks:write   tasks:move   tasks:delete
docs:read    docs:write
members:read members:write   apikeys:manage
```

## Agent flows (the Maestro Loop via API)

### A. Briefing → spec + task tree (decompose)

```bash
# 1) (optional) register the refined spec as a document
curl -X POST http://localhost:5099/api/documents -H "x-api-key: $KEY" \
  -H 'Content-Type: application/json' \
  -d '{"projectId":2,"type":"SPEC","title":"Navbar spec","body":"# ...markdown..."}'

# 2) decompose into tasks + subtasks + dependencies, in a single transaction
curl -X POST http://localhost:5099/api/tasks/bulk -H "x-api-key: $KEY" \
  -H 'Content-Type: application/json' -H 'Idempotency-Key: brief-2026-06-22-navbar' \
  -d '{
    "projectId": 2,
    "items": [{
      "ref": "nav",
      "title": "Add '\''Projects'\'' tab to the navbar",
      "objective": "Access the project list directly from the navbar.",
      "acceptance": "Item visible on desktop and mobile, /projects route, active state ok.",
      "priority": "HIGH", "estimateMd": 1.5,
      "subtasks": [
        { "ref": "design",  "title": "Define position, label and icon", "estimateMd": 0.25 },
        { "ref": "desktop", "title": "Link in the desktop navbar", "dependsOn": ["design"], "estimateMd": 0.5 },
        { "ref": "mobile",  "title": "Add to the mobile menu", "dependsOn": ["design"], "estimateMd": 0.5 },
        { "ref": "active",  "title": "routerLinkActive on /projects", "dependsOn": ["desktop","mobile"] },
        { "ref": "qa",      "title": "Test navigation and responsiveness", "dependsOn": ["active"] }
      ]
    }]
  }'
```

> `ref` is a local alias in the payload; `dependsOn` references other `ref`s of the
> same batch. The API resolves the `ref`s to real IDs and creates the `TaskDependency` in
> the same transaction — the **flow is born ready** already at decompose time (see [doc 08](08-fluxo-de-tarefas.md)).

### B. See the flow (objective → steps → acceptance)

```bash
curl "http://localhost:5099/api/tasks/MAESTRO-4/flow" -H "x-api-key: $KEY"
```

Response (abridged):

```json
{
  "task": { "code": "MAESTRO-4", "title": "Add 'Projects' tab to the navbar",
            "objective": "...", "acceptance": "..." },
  "progress": { "done": 1, "total": 5 },
  "nodes": [
    { "id": "objetivo", "kind": "entry", "label": "..." },
    { "id": "t12", "code": "MAESTRO-5", "title": "Define position...", "state": "done" },
    { "id": "t13", "code": "MAESTRO-6", "title": "Desktop link",       "state": "todo" },
    { "id": "t14", "code": "MAESTRO-7", "title": "Mobile menu",        "state": "todo" },
    { "id": "t15", "code": "MAESTRO-8", "title": "routerLinkActive",   "state": "blocked" },
    { "id": "t16", "code": "MAESTRO-9", "title": "Test",               "state": "blocked" },
    { "id": "aceite", "kind": "exit", "label": "..." }
  ],
  "edges": [ { "from": "objetivo", "to": "t12" }, { "from": "t12", "to": "t13" }, "..." ]
}
```

Each subtask's `state` (`todo` / `blocked` / `done`) is **computed** from the
dependencies and the current column. Use `?format=mermaid` to receive `{ "mermaid": "graph TD ..." }`.

### C. Execution → move on the board

```bash
# columns come from the board: GET /api/projects/:id/board → columns[].id
curl -X POST http://localhost:5099/api/tasks/MAESTRO-5/move -H "x-api-key: $KEY" \
  -H 'Content-Type: application/json' -d '{"columnId":10}'   # → Done
```

When `MAESTRO-5` is completed, its dependents (`MAESTRO-6`, `MAESTRO-7`) move from
`blocked` to `todo` automatically on the next `flow`.

## MCP server (API wrapper)

The `mcp/` package exposes the API as an **MCP server** (stdio), so that agents like
Claude Code can talk to it natively, without writing REST by hand. The key
(`MAESTRO_API_KEY`) goes in the MCP server config; the tenant comes from the key itself.
Exposed tools (e.g.): create project, write doc, decompose into tasks, list
tasks, move on the board, comment.

## Security

- API key: stored **only as a hash** (SHA-256); the secret is shown once; the `prefix`
  is visible in the UI to identify the key.
- Optional `expiresAt` + immediate revocation (`revokedAt`).
- Every action via key enters the `ActivityLog` as "via agent".
- *Planned refinements:* rate limit per key, `lastUsedAt` to detect idle
  keys, and enforcement per `scope`.
