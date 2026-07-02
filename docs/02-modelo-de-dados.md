> 🇧🇷 [Versão em português](02-modelo-de-dados.ptbr.md)

# 02 — Data model

Multi-tenant by **Company**. Recommended isolation strategy:
**row-level** — every domain table carries `companyId` and every query is filtered
by it (simple, sufficient, easy to audit). See [doc 04](04-rbac-e-multitenant.md).

## Entities

| Entity | Role |
|---|---|
| **User** | global identity (already comes from the template). May belong to several companies. |
| **Company** | the company (tenant). Has members, projects, boards, API keys. |
| **Membership** | links `User ↔ Company` with a **Role**. This is where the user's role *in that* company lives. |
| **ApiKey** | agent credential, linked to a Membership. Has scopes, hash, expiration, revocation. |
| **Project** | unit of work within the company. Has docs, board(s), tasks. |
| **Board** | kanban board of a project. Has columns. |
| **Column** | board column/status (Backlog, To do, Doing, Review, Done…), with order and optional WIP. |
| **Task** | task in a column. Self-relational for **subtasks** (`parentId`). Has an **objective** and an **acceptance criterion** (acceptance point). |
| **TaskDependency** | **precedence** edge between tasks/subtasks (`blocker → blocked`). Forms the flow graph (DAG). |
| **Document** | versioned markdown doc, linked to a Project or Task. |
| **Comment** | comment on a task. |
| **Label** | label/tag per company, applicable to tasks. |
| **ActivityLog** | audit trail: actor (user + whether via API key), action, before/after. |

## Relationships (summary)

```
User 1───* Membership *───1 Company
Company 1───* Project 1───* Board 1───* Column 1───* Task
Task *───1 Task (parentId → subtasks)
Task *───* Task (TaskDependency: blocker → blocked → flow/DAG)
Task *───* Label
Project/Task 1───* Document
Task 1───* Comment
Company 1───* ApiKey (via Membership)
* ───* ActivityLog (polymorphic per entity)
```

## Roles (enum Role, on the Membership)

`OWNER` · `MANAGER` · `TECH_LEAD` · `DEV` · `VIEWER`
(permission matrix in [doc 04](04-rbac-e-multitenant.md))

## Prisma sketch (partial)

> Reuses the `User` from the template; adds the domain. MySQL (from the template).

```prisma
model Company {
  id          String       @id @default(cuid())
  name        String
  slug        String       @unique
  memberships Membership[]
  projects    Project[]
  apiKeys     ApiKey[]
  labels      Label[]
  createdAt   DateTime     @default(now())
}

model Membership {
  id        String   @id @default(cuid())
  user      User     @relation(fields: [userId], references: [id])
  userId    String
  company   Company  @relation(fields: [companyId], references: [id])
  companyId String
  role      Role     @default(DEV)
  apiKeys   ApiKey[]
  createdAt DateTime @default(now())
  @@unique([userId, companyId])   // 1 role per user per company
}

enum Role { OWNER MANAGER TECH_LEAD DEV VIEWER }

model ApiKey {
  id           String     @id @default(cuid())
  label        String     // "claude-code agent", etc.
  hashedKey    String     @unique   // only the hash; the secret is shown once at creation
  prefix       String     // first chars to identify it in the UI
  membership   Membership @relation(fields: [membershipId], references: [id])
  membershipId String
  company      Company    @relation(fields: [companyId], references: [id])
  companyId    String
  scopes       Json       // e.g.: ["tasks:write","docs:write","tasks:move"]
  lastUsedAt   DateTime?
  expiresAt    DateTime?
  revokedAt    DateTime?
  createdAt    DateTime   @default(now())
}

model Project {
  id          String     @id @default(cuid())
  company     Company    @relation(fields: [companyId], references: [id])
  companyId   String
  name        String
  key         String     // short prefix for task code (e.g.: "GAV")
  description String?    @db.Text
  boards      Board[]
  tasks       Task[]
  documents   Document[]
  createdAt   DateTime   @default(now())
  @@unique([companyId, key])
}

model Board {
  id        String   @id @default(cuid())
  project   Project  @relation(fields: [projectId], references: [id])
  projectId String
  name      String   @default("Principal")
  columns   Column[]
}

model Column {
  id       String @id @default(cuid())
  board    Board  @relation(fields: [boardId], references: [id])
  boardId  String
  name     String   // "To do", "Doing", "Review", "Done"
  order    Int
  wipLimit Int?
  tasks    Task[]
}

model Task {
  id          String     @id @default(cuid())
  company     Company    @relation(fields: [companyId], references: [id])
  companyId   String
  project     Project    @relation(fields: [projectId], references: [id])
  projectId   String
  column      Column     @relation(fields: [columnId], references: [id])
  columnId    String
  number      Int        // sequential per project → "GAV-42"
  title       String
  description String?    @db.Text          // markdown (detail)
  objective   String?    @db.Text          // the task's OBJECTIVE (the flow's entry)
  acceptance  String?    @db.Text          // ACCEPTANCE CRITERION (the acceptance point)
  parent      Task?      @relation("Subtasks", fields: [parentId], references: [id])
  parentId    String?
  subtasks    Task[]     @relation("Subtasks")
  assignee    User?      @relation(fields: [assigneeId], references: [id])
  assigneeId  String?
  priority    Priority   @default(MEDIUM)
  estimateMd  Float?     // estimate in PERSON-DAYS
  rank        String     // kanban ordering (lexorank/fractional)
  // flow edges (precedence between tasks/subtasks)
  blocking    TaskDependency[] @relation("Blocker")  // tasks that THIS one blocks
  blockedBy   TaskDependency[] @relation("Blocked")  // tasks that block THIS one
  labels      Label[]
  comments    Comment[]
  documents   Document[]
  createdAt   DateTime   @default(now())
  updatedAt   DateTime   @updatedAt
  @@unique([projectId, number])
}

// Precedence edge: blocker must complete before blocked.
// Typically links subtasks of the SAME parent task (but can link tasks).
model TaskDependency {
  id         String @id @default(cuid())
  companyId  String
  blocker    Task   @relation("Blocker", fields: [blockerId], references: [id])
  blockerId  String
  blocked    Task   @relation("Blocked", fields: [blockedId], references: [id])
  blockedId  String
  createdAt  DateTime @default(now())
  @@unique([blockerId, blockedId])         // no duplicate edge
}

enum Priority { LOW MEDIUM HIGH URGENT }

model Document {
  id        String   @id @default(cuid())
  company   Company  @relation(fields: [companyId], references: [id])
  companyId String
  title     String
  body      String   @db.LongText        // markdown
  type      DocType  @default(SPEC)
  version   Int      @default(1)
  project   Project? @relation(fields: [projectId], references: [id])
  projectId String?
  task      Task?    @relation(fields: [taskId], references: [id])
  taskId    String?
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}

enum DocType { SPEC PLAN NOTES ADR OTHER }

model ActivityLog {
  id          String   @id @default(cuid())
  companyId   String
  actorUserId String                       // always a user…
  viaApiKeyId String?                      // …but flags whether it was an agent
  entityType  String                       // "Task", "Document", "Membership"…
  entityId    String
  action      String                       // "created","moved","status_changed"…
  changes     Json?                        // before/after diff
  createdAt   DateTime @default(now())
}
```

## Modeling decisions

- **Subtask = Task with `parentId`** (self-relational), not a separate entity —
  it reuses all the behavior (status, assignee, doc, estimate). A simple
  checklist could be a `Json` field in a future phase, if needed.
- **Status = board column** — the status is the `Column` the task is in.
  Configurable boards → configurable statuses, with no rigid enum.
- **`number` sequential per project** → readable codes (`GAV-42`), good for the
  agent to reference and for humans to talk about.
- **`estimateMd` in person-days** — aligned with the preference to document effort in
  person-days, without allocating people.
- **API key stores only the hash** — the secret is shown only once at creation.
- **Task has `objective` + `acceptance`** — the task is the *entry* of the flow
  (objective) and has an *acceptance point* (acceptance criterion); the subtasks are the
  steps to get there. See [doc 08 — Task flow](08-fluxo-de-tarefas.md).
- **`TaskDependency` forms a DAG** — the precedence edges between subtasks
  produce the task's flowchart. It must be **acyclic** (validate on creation); with no
  edges, subtasks are treated as parallel (entry → each one → acceptance).
