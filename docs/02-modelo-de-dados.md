# 02 — Modelo de dados

Multi-tenant por **Empresa (Company)**. Estratégia de isolamento recomendada:
**row-level** — toda tabela de domínio carrega `companyId` e toda query é filtrada
por ele (simples, suficiente, fácil de auditar). Ver [doc 04](04-rbac-e-multitenant.md).

## Entidades

| Entidade | Papel |
|---|---|
| **User** | identidade global (já vem do template). Pode pertencer a várias empresas. |
| **Company** | a empresa (tenant). Tem membros, projetos, quadros, API keys. |
| **Membership** | liga `User ↔ Company` com um **Role**. É onde mora o papel do usuário *naquela* empresa. |
| **ApiKey** | credencial de agente, vinculada a uma Membership. Tem escopos, hash, expiração, revogação. |
| **Project** | unidade de trabalho dentro da empresa. Tem docs, quadro(s), tarefas. |
| **Board** | quadro kanban de um projeto. Tem colunas. |
| **Column** | coluna/status do quadro (Backlog, A fazer, Fazendo, Revisão, Concluído…), com ordem e WIP opcional. |
| **Task** | tarefa numa coluna. Auto-relacional para **subtarefas** (`parentId`). Tem **objetivo** e **critério de aceite** (ponto de aceitação). |
| **TaskDependency** | aresta de **precedência** entre tarefas/subtarefas (`blocker → blocked`). Forma o grafo (DAG) do fluxo. |
| **Document** | doc markdown versionada, ligada a Project ou Task. |
| **Comment** | comentário em tarefa. |
| **Label** | etiqueta/tag por empresa, aplicável a tarefas. |
| **ActivityLog** | trilha de auditoria: ator (user + se via API key), ação, antes/depois. |

## Relacionamentos (resumo)

```
User 1───* Membership *───1 Company
Company 1───* Project 1───* Board 1───* Column 1───* Task
Task *───1 Task (parentId → subtarefas)
Task *───* Task (TaskDependency: blocker → blocked → fluxo/DAG)
Task *───* Label
Project/Task 1───* Document
Task 1───* Comment
Company 1───* ApiKey (via Membership)
* ───* ActivityLog (polimórfico por entidade)
```

## Papéis (enum Role, na Membership)

`OWNER` · `MANAGER` · `TECH_LEAD` · `DEV` · `VIEWER`
(matriz de permissões no [doc 04](04-rbac-e-multitenant.md))

## Esboço Prisma (parcial)

> Reaproveita o `User` do template; adiciona o domínio. MySQL (do template).

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
  @@unique([userId, companyId])   // 1 papel por usuário por empresa
}

enum Role { OWNER MANAGER TECH_LEAD DEV VIEWER }

model ApiKey {
  id           String     @id @default(cuid())
  label        String     // "agente claude-code", etc.
  hashedKey    String     @unique   // só o hash; o segredo é exibido 1x na criação
  prefix       String     // primeiros chars p/ identificar na UI
  membership   Membership @relation(fields: [membershipId], references: [id])
  membershipId String
  company      Company    @relation(fields: [companyId], references: [id])
  companyId    String
  scopes       Json       // ex.: ["tasks:write","docs:write","tasks:move"]
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
  key         String     // prefixo curto p/ código de tarefa (ex.: "GAV")
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
  name     String   // "A fazer", "Fazendo", "Revisão", "Concluído"
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
  number      Int        // sequencial por projeto → "GAV-42"
  title       String
  description String?    @db.Text          // markdown (detalhe)
  objective   String?    @db.Text          // o OBJETIVO da tarefa (a entrada do fluxo)
  acceptance  String?    @db.Text          // CRITÉRIO DE ACEITE (o ponto de aceitação)
  parent      Task?      @relation("Subtasks", fields: [parentId], references: [id])
  parentId    String?
  subtasks    Task[]     @relation("Subtasks")
  assignee    User?      @relation(fields: [assigneeId], references: [id])
  assigneeId  String?
  priority    Priority   @default(MEDIUM)
  estimateMd  Float?     // estimativa em HOMEM-DIA
  rank        String     // ordenação no kanban (lexorank/fractional)
  // arestas do fluxo (precedência entre tarefas/subtarefas)
  blocking    TaskDependency[] @relation("Blocker")  // tarefas que ESTA bloqueia
  blockedBy   TaskDependency[] @relation("Blocked")  // tarefas que bloqueiam ESTA
  labels      Label[]
  comments    Comment[]
  documents   Document[]
  createdAt   DateTime   @default(now())
  updatedAt   DateTime   @updatedAt
  @@unique([projectId, number])
}

// Aresta de precedência: blocker precisa concluir antes de blocked.
// Tipicamente liga subtarefas da MESMA tarefa-pai (mas pode ligar tarefas).
model TaskDependency {
  id         String @id @default(cuid())
  companyId  String
  blocker    Task   @relation("Blocker", fields: [blockerId], references: [id])
  blockerId  String
  blocked    Task   @relation("Blocked", fields: [blockedId], references: [id])
  blockedId  String
  createdAt  DateTime @default(now())
  @@unique([blockerId, blockedId])         // sem aresta duplicada
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
  actorUserId String                       // sempre um usuário…
  viaApiKeyId String?                      // …mas marca se foi um agente
  entityType  String                       // "Task", "Document", "Membership"…
  entityId    String
  action      String                       // "created","moved","status_changed"…
  changes     Json?                        // diff antes/depois
  createdAt   DateTime @default(now())
}
```

## Decisões de modelagem

- **Subtarefa = Task com `parentId`** (auto-relacional), não uma entidade à parte —
  reaproveita todo o comportamento (status, assignee, doc, estimativa). Checklist
  simples pode ser um campo `Json` numa fase futura, se necessário.
- **Status = coluna do quadro** — o status é a `Column` em que a tarefa está.
  Quadros configuráveis → status configuráveis, sem enum rígido.
- **`number` sequencial por projeto** → códigos legíveis (`GAV-42`), bons para o
  agente referenciar e para humanos conversarem.
- **`estimateMd` em homem-dia** — alinhado à preferência de documentar esforço em
  homem-dia, sem alocação de pessoas.
- **API key guarda só o hash** — segredo mostrado uma única vez na criação.
- **Tarefa tem `objective` + `acceptance`** — a tarefa é a *entrada* do fluxo
  (objetivo) e tem um *ponto de aceitação* (critério de aceite); as subtarefas são os
  passos para chegar lá. Ver [doc 08 — Fluxo de tarefas](08-fluxo-de-tarefas.md).
- **`TaskDependency` forma um DAG** — as arestas de precedência entre subtarefas
  geram o fluxograma da tarefa. Deve ser **acíclico** (validar na criação); sem
  arestas, as subtarefas são tratadas como paralelas (entrada → cada uma → aceite).
