> 🇧🇷 [Versão em português](07-frontend-angular.ptbr.md)

# 07 — Frontend Angular

Decision [D1](06-decisoes-em-aberto.md#d1--frontend-angular-ou-react--decidido-angular):
the front is **Angular** (`front/` from the template). Remove `front-react/` and `front-flutter/`.

## Stack

| Item | Technology |
|---|---|
| Framework | Angular 20 (standalone components, no NgModules) |
| State | NgRx (store per feature) + signals for local state |
| Style | Tailwind CSS + Bootstrap (already in the template) |
| Drag-and-drop | **Angular CDK** (`@angular/cdk/drag-drop`) — for the kanban |
| Flow graph | **`@swimlane/ngx-graph`** (dagre) — task flowchart (doc 08) |
| Markdown | `ngx-markdown` (render) + textarea editor with preview |
| Alerts | SweetAlert2 (already in the template) |
| HTTP | `HttpClient` + interceptors (JWT, refresh, X-Company-Id, errors) |
| PWA/Mobile | Capacitor (already in the template) |

> Where the template already delivers login/refresh/profile, **reuse** — just add the domain.

## Folder structure (feature-based)

```
front/src/app/
├── core/                  # singletons: guards, interceptors, auth, config
│   ├── auth/              # (from the template) login, refresh, guard
│   ├── interceptors/      # jwt, company-context (X-Company-Id), error
│   └── tenant/            # active company service (signal)
├── shared/                # reusable components/pipes/directives
│   └── ui/                # buttons, modal, priority badge, avatar...
├── features/
│   ├── companies/         # list/select/create company, members
│   ├── projects/          # list/create project
│   ├── board/             # kanban board (DnD)
│   ├── tasks/             # task detail/editing + subtasks
│   ├── docs/              # markdown editor/viewer
│   └── settings/          # members, API keys
└── state/                 # NgRx (actions/reducers/effects/selectors) per feature
```

## Company context (multi-tenant on the front)

- A `TenantService` holds the **active company** (signal), persisted in storage.
- An **interceptor** injects `X-Company-Id` into every request.
- A **company selector** in the header switches the context (the user may have several).
- Switching company clears the domain stores (board/tasks) and refetches.

See the auth/context flow in [`diagramas/auth-rbac.svg`](diagramas/auth-rbac.svg).

## Kanban board (CDK drag-drop)

Components:

- `BoardComponent` — loads the board (columns + tasks) via NgRx; orchestrates DnD.
- `ColumnComponent` — a column (`cdkDropList`), accepts drops and shows WIP.
- `TaskCardComponent` — card (`cdkDrag`): title, `GAV-42` code, assignee,
  priority, estimate (pd), labels.
- `TaskDetailComponent` — modal/panel: editing, subtasks, comments, docs, activity.

Drop behavior:

1. `cdkDropListDropped` → **optimistic update** in the store (move the card in the UI).
2. Fires `POST /tasks/:code/move { columnId, rank }`.
3. On error → **rollback** + SweetAlert. On success → confirm the server's `rank`.
4. Lexicographic `rank` (see [D4](06-decisoes-em-aberto.md#d4--ordenação-no-kanban-rank-fracionário-lexorank-vs-order-inteiro)) → moving = 1 PATCH.

## Task flow (`ngx-graph`)

Visualization of the objective → subtasks → acceptance flow (concept in [doc 08](08-fluxo-de-tarefas.md)).

- **Lib:** `@swimlane/ngx-graph` (dagre layout, pan/zoom, custom node template).
- `TaskFlowComponent` — consumes `GET /tasks/:code/flow` (`{ nodes, edges }`) and draws
  the DAG. Lives in a tab of `TaskDetailComponent` ("Flow"), next to "Subtasks".
- **Node template:** title, `GAV-42` code, assignee, **color by status** and a lock
  when `blocked`; synthetic **Objective** (entry) and **Acceptance** (exit) nodes.
- **Interactions:**
  - clicking a node → opens the subtask detail;
  - dragging from one node to another → `POST /dependencies` (creates an edge, validates cycle);
  - moving a subtask on the kanban → recolors the node (derives from the same status).
- **No dependencies** → default render `entry → (subtasks in parallel) → acceptance`.
- The same component serves the **project flow** (nodes = tasks), switching the source.
- **Export:** an "export Mermaid" button uses `?format=mermaid` to embed the flow in
  the task's markdown doc.

## State (NgRx)

- One slice per feature: `companies`, `projects`, `board`, `tasks`, `docs`, `members`.
- Effects make the HTTP calls; selectors derive the view (e.g., tasks per column).
- Ephemeral UI state (modals, drafts) lives in local **signals**, outside the store.

## Markdown documents

- `DocViewerComponent` — render with `ngx-markdown`.
- `DocEditorComponent` — editor with side-by-side preview + **export `.md`** button
  (preserves the current flow of sending markdown to the team).
- Docs live on projects and tasks (same `Document` entity).

## Routes (lazy)

```
/login                                  (template)
/companies                              company selection/creation
/:companyId/projects                    project list
/:companyId/projects/:id/board          kanban board
/:companyId/projects/:id/docs           project documents
/:companyId/tasks/:code                 task detail (deep-link GAV-42)
/:companyId/settings/members            member and role management
/:companyId/settings/api-keys           API key management (agents)
```

Each feature is **lazy-loaded** by route. Guards: `authGuard` (template) + `tenantGuard`
(requires active company) + `roleGuard` (hides management screens for DEV/VIEWER).

## API integration

- Generate the **types/clients from the API's Swagger** (`openapi-generator` or
  `ng-openapi-gen`) to avoid hand-writing DTOs and keep the front in sync.
- Standardize error handling (interceptor) so messages coming from the API
  (insufficient scope, validation) turn into friendly toasts.

## Definition of Done (frontend)

- [ ] Login/refresh reusing the template, with a functional company selector.
- [ ] Kanban board with DnD, optimistic update and rollback.
- [ ] Task detail with subtasks, comments and docs.
- [ ] "Flow" tab (ngx-graph) with nodes colored by status, clickable, and Mermaid export.
- [ ] Markdown editor/viewer with `.md` export.
- [ ] Member and API key screens protected by role.
- [ ] Types generated from Swagger; no `any` in the API contracts.
- [ ] Responsive + dark mode; lint and build with no errors.
