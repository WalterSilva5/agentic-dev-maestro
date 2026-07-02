> 🇧🇷 [Versão em português](08-fluxo-de-tarefas.ptbr.md)

# 08 — Task flow (objective → subtasks → acceptance)

The platform **displays each task as a flowchart**, not just as a list of
subtasks. The idea:

> A **task** is the *entry point* of the flow: it has an **objective** and an
> **acceptance point** (acceptance criterion). To reach acceptance, you need to
> complete the **steps** — the **subtasks** — which may have **dependencies**
> among them.

Rendered example: [`diagramas/fluxo-tarefa-exemplo.svg`](diagramas/fluxo-tarefa-exemplo.svg)

![Task flow example](diagramas/fluxo-tarefa-exemplo.svg)

## What this adds to the model

Details in [doc 02](02-modelo-de-dados.md). Summary:

- `Task.objective` — the **objective** (flow entry point).
- `Task.acceptance` — the **acceptance criterion** (acceptance point).
- `TaskDependency` — a **precedence** edge `blocker → blocked` between tasks/
  subtasks. The set of edges forms a **DAG** (acyclic graph).

## Two flow levels (same mechanics)

1. **Flow of a task** — nodes = subtasks; edges = dependencies among them.
   This is the main case (the example above).
2. **Flow of a project** — nodes = tasks; edges = dependencies among tasks.
   Same structure (`TaskDependency`), only the displayed level changes.

## How the graph is built

Given a task and its subtasks + dependencies, the backend produces a graph with
two **synthetic nodes**:

- **Entry** (`objective`) → links to the **root** subtasks (with no `blocker`).
- **Acceptance** (`acceptance`) ← receives from the **leaf** subtasks (with no `blocked`).

Rules:

- **No dependencies** → all subtasks are both root and leaf: the flow becomes
  `entry → (each subtask in parallel) → acceptance`. It does not invent an order that doesn't exist.
- **With dependencies** → the layout follows the precedence (sequence, branching,
  parallel + join), as in the example (A‖B → C → D → acceptance).
- **DAG required** → cycles are rejected when the edge is created (see validation).

## Node state and colors

The node color reflects the status (the kanban column where the subtask sits):

| Node | Meaning |
|---|---|
| 🟩 completed | subtask in a "completed" column |
| 🟨 in progress | subtask in "doing"/"review" |
| ⬜ to do | not yet started |
| 🔒 blocked | has a `blocker` not yet completed (cannot start) |
| 🟦 acceptance | terminal node; **unlocks when all subtasks are completed** |

- **Blocking is derived**, not a manual status: a subtask is blocked if
  any dependency (`blocker`) is not completed.
- **Task progress** = % of completed subtasks; the acceptance node indicates
  "ready to accept" when 100% + acceptance criteria are met.

## Validation (DAG)

- When creating a `TaskDependency`, reject if the edge creates a **cycle** (depth-
  first search starting from `blocked` looking for `blocker`).
- Reject self-dependency (`blockerId == blockedId`).
- Dependencies normally link subtasks of the **same parent task**; linking tasks
  from different projects/companies is forbidden (same `companyId`).

## Rendering on the platform

| Where | Technology | Why |
|---|---|---|
| **Inside the app** (interactive) | **`@swimlane/ngx-graph`** (Angular + dagre) | custom nodes with status/color, clickable, pan/zoom, automatic DAG layout |
| **Export / markdown docs** | **Mermaid** (`flowchart`) | renders natively on GitHub/Obsidian; ships with the doc exported from the task |
| **Static repo docs** | PlantUML (as in `docs/diagramas/`) | keeps the standard of the architecture diagrams |

- **In-app:** `ngx-graph` receives `{ nodes, edges }` from the API and uses its own
  node template (title, code `GAV-42`, assignee, color by status, padlock if blocked).
  Clicking a node opens the subtask detail; the layout (dagre) is automatic.
- **Export:** the API also emits the same graph as **Mermaid** to embed in the task's
  markdown doc (the artifact the team receives). E.g.:

  ```mermaid
  flowchart TD
    OBJ([Objetivo: login com refresh]) --> A[A. Modelar sessões]
    OBJ --> B[B. Endpoint de login]
    A --> C[C. Endpoint de refresh]
    B --> C
    C --> D[D. Testes e2e]
    D --> ACE([Aceite: loga + renova + testes verdes])
  ```

## Interactions (app)

- **Click a node** → opens the subtask detail.
- **Link two nodes** (drag from one to another) → creates a `TaskDependency` (with
  cycle validation); undo removes the edge.
- **Move a subtask on the kanban** → recolors the node automatically (same state).
- *(future)* highlight the **critical path** and subtasks blocking acceptance.

## API (summary — details in doc 03)

- `GET /tasks/:code/flow` → `{ nodes, edges }` (and `?format=mermaid` → Mermaid text).
- `POST /tasks/:code/dependencies` `{ blockerCode, blockedCode }` (validates DAG).
- `DELETE /tasks/:code/dependencies/:depId`.
- In `POST /tasks/bulk` (decompose), the agent can already send `dependsOn` in each
  subtask → the edges are created along with it. This way the **flow is born ready** in
  the decompose step of the [Maestro Loop](diagramas/maestro-loop.svg).

## Why this matters

- It makes explicit **what is missing** to accept the task and **what is blocking** what.
- The agent, during decompose, already describes the **path** (not just a loose list).
- Managers/tech leads can see bottlenecks without reading all the subtasks.
