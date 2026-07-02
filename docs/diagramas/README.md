> 🇧🇷 [Versão em português](README.ptbr.md)

# Diagrams

Maestro flowcharts in **PlantUML** (`.puml` — source) + **SVG** (rendered).
Whenever you edit a `.puml`, regenerate the SVGs:

```bash
./gerar.sh        # baixa o plantuml.jar (1x) e gera todos os .svg
```

Requirements: Java + Graphviz (`dot`). The jar lives in `.plantuml.jar` (git-ignored).

---

## 1. Architecture (components)

Overview: Angular frontend, NestJS backend (auth, multi-tenant context, domain,
queues), MCP server, MySQL and Redis — and how humans and agents come in.

![Architecture](arquitetura.svg)

Source: [`arquitetura.puml`](arquitetura.puml)

## 2. Maestro Loop (main flow)

The product cycle: briefing → refinement → decompose → board → execution → overview.

![Maestro Loop](maestro-loop.svg)

Source: [`maestro-loop.puml`](maestro-loop.puml)

## 3. Data model (ER)

Entities and relationships (details in [`../02-modelo-de-dados.md`](../02-modelo-de-dados.md)).

![Data model](modelo-dados.svg)

Source: [`modelo-dados.puml`](modelo-dados.puml)

## 4. Agent flow (sequence)

How the agent turns a briefing into a doc + tasks on the board, via API key.

![Agent flow](fluxo-agente.svg)

Source: [`fluxo-agente.puml`](fluxo-agente.puml)

## 5. Authentication and RBAC (sequence)

Context resolution (JWT vs. API key) and effective permission = role ∩ scopes.

![Auth and RBAC](auth-rbac.svg)

Source: [`auth-rbac.puml`](auth-rbac.puml)

## 6. Task states (kanban)

Standard transitions of a task between the board columns.

![Task states](kanban-estados.svg)

Source: [`kanban-estados.puml`](kanban-estados.puml)

## 7. Flow of a task (objective → subtasks → acceptance)

Example of the flowchart the platform displays per task: the entry (objective), the
steps (subtasks with dependencies, colored by status) and the acceptance point.
Concept and in-app rendering in [`../08-fluxo-de-tarefas.md`](../08-fluxo-de-tarefas.md).

![Task flow example](fluxo-tarefa-exemplo.svg)

Source: [`fluxo-tarefa-exemplo.puml`](fluxo-tarefa-exemplo.puml)
