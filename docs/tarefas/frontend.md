> 🇧🇷 [Versão em português](frontend.ptbr.md)

# Tasks — Frontend (Angular 20)

Base: the template's `front/` (login/refresh/profile ready). Architecture in
[doc 07](../07-frontend-angular.md). Effort in man-days (md).

---

## Phase 1 — Task and board core

### F1.0 — Setup and cleanup · 0.5 md
- [ ] Copy the template's `front/`; remove `front-react/` and `front-flutter/`
- [ ] Bring up the front end and validate login against the API
- [ ] Install new deps: `@angular/cdk`, `ngx-markdown`, `@swimlane/ngx-graph`

### F1.1 — Company context (multi-tenant) · 1.5 md
- [ ] `TenantService` with the active company (signal + storage)
- [ ] Interceptor that injects `X-Company-Id`
- [ ] Company selector in the header; switching clears domain stores
- [ ] `tenantGuard` (requires an active company)

### F1.2 — Project list/creation · 1.5 md
- [ ] Projects screen (list + create)
- [ ] `projects` NgRx slice (effects + selectors)
- [ ] Navigation to the project board

### F1.3 — Kanban board with CDK drag-drop · 4 md
- [ ] `BoardComponent` loading columns + tasks (`board` slice)
- [ ] `ColumnComponent` (`cdkDropList`) with a WIP indicator
- [ ] `TaskCardComponent` (`cdkDrag`): code, assignee, priority, estimate, labels
- [ ] Drop → **optimistic update** + `POST /move` + **rollback** on error
- [ ] Quick task creation in the column (inline)

### F1.4 — Task detail · 2.5 md
- [ ] `TaskDetailComponent` (modal/panel): edit fields, priority, estimate
- [ ] **Objective** and **acceptance criteria** fields (markdown)
- [ ] Subtasks (list/create/complete)
- [ ] Comments
- [ ] Deep-link `/:companyId/tasks/:code`

### F1.5 — Task flow tab (ngx-graph) · 3 md
> Feature from [doc 08](../08-fluxo-de-tarefas.md).
- [ ] `TaskFlowComponent` consuming `GET /tasks/:code/flow` (`{ nodes, edges }`)
- [ ] Node template: title, code, assignee, **color by status** + lock icon if blocked
- [ ] Synthetic **Objective** (entry) and **Acceptance** (exit) nodes
- [ ] Click node → open subtask; dagre layout + pan/zoom
- [ ] Drag node→node → `POST /dependencies` (with invalid-cycle feedback)
- [ ] **Export Mermaid** button (`?format=mermaid`)
- [ ] Reuse for the **project flow** (nodes = tasks)

---

## Phase 2 — Docs and activity

### F2.1 — Markdown documents · 2.5 md
- [ ] `DocViewerComponent` (render `ngx-markdown`)
- [ ] `DocEditorComponent` (side-by-side edit + preview)
- [ ] **Export `.md`** button
- [ ] Docs on the project and on the task

### F2.2 — Activity/audit tab · 1.5 md
- [ ] `ActivityLog` timeline on the task and the project
- [ ] "via agent" badge when the action came from an API key

---

## Phase 4 — Settings and vision

### F4.1 — Member management · 1.5 md
- [ ] Members screen (list, invite, change role, remove)
- [ ] `roleGuard` hides management from DEV/VIEWER

### F4.2 — API key management · 1.5 md
- [ ] List keys (label, prefix, lastUsed, expiry)
- [ ] Create key → show secret **once** (copy) + choose scopes
- [ ] Revoke key

### F4.3 — Manager dashboard · 2.5 md
- [ ] Progress by project/company (tasks by status, by assignee)
- [ ] Filters and search (status, label, assignee, text)

---

## Cross-cutting

### FX.1 — Types generated from Swagger · 1 md
- [ ] Configure `ng-openapi-gen` (or `openapi-generator`) pointing at `/api/docs-json`
- [ ] `npm run gen:api` script + use the types in the services

### FX.2 — UX and theme · 1 md
- [ ] Responsive + dark mode
- [ ] Standardized error handling (interceptor → SweetAlert2 toasts)

---

## Quality checklist (frontend)

- [ ] Kanban with smooth DnD, optimistic update and rollback tested
- [ ] No `any` in the API contracts (Swagger types)
- [ ] Management screens protected by role
- [ ] API key secret shown only once, with copy
- [ ] Lazy loading per route; lint and build without errors
- [ ] Responsive and dark mode validated
