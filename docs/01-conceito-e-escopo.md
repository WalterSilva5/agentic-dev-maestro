> 🇧🇷 [Versão em português](01-conceito-e-escopo.ptbr.md)

# 01 — Concept and scope

## The problem

Today the workflow with agents is:

1. I receive a task/project (a raw description, sometimes vague).
2. I hand the description to an agent.
3. Together we optimize the documentation and generate a list of tasks/subtasks/tips.
4. The resulting markdown files go to other devs and managers, giving them visibility into the project.

This **works**, but the artifacts end up loose (`.md` files scattered around), without
state (what's in progress? who did what?), without standardization, and without a single
place where humans and agents share the truth. You can't see progress, nor
audit what an agent changed.

## The solution

A **backend + frontend** application that becomes the system of record for this workflow:

- The agent accesses the **API** to create tasks, subtasks, and documentation.
- The agent **changes the status** of tasks following a configurable **kanban board**.
- The optimized documentation lives **attached** to the project/task (markdown, versioned,
  exportable) — the same artifact that today is sent to devs and managers.
- Everything is **multi-company**: users are linked to companies and are managed by
  the company's owners.
- Agents act via an **API key linked to a user**, inheriting their permissions and
  leaving an audit trail (human vs. agent).

## Personas

| Persona | Uses Maestro to |
|---|---|
| **Dev** | see their tasks, move them on the board, read the docs/tips, comment, open linked PRs |
| **Tech Lead** | review, approve, adjust decomposition, ensure technical quality |
| **Manager** | progress view by project/company, without getting into technical detail |
| **AI Agent** | refine briefings into docs, decompose into tasks/subtasks, move status, record progress — all via API key |

## Differentiators (the "why build it")

1. **Agent as a first-class citizen** — it's not an integration bolted on top:
   the agent has an identity (API key), permission scopes, and auditing.
2. **Built-in spec → tasks pipeline** — refine + decompose is the central feature.
3. **Native, exportable markdown docs** — preserves the current workflow (sending `.md`
   files to the team), but with state and version.
4. **Effort in person-days, no allocation** — estimates in person-days; allocating
   people and setting the schedule is up to leadership. Maestro does not staff the team.
5. **MCP server** — any agent (Claude Code, etc.) talks natively to the boards
   via MCP, in addition to REST.

## MVP scope (what's included)

- Companies + user membership (members) + roles.
- Projects within companies.
- Kanban boards with configurable columns/statuses.
- Tasks and subtasks (move, assign, prioritize, estimate in person-days, tags).
- Markdown documents on project/task.
- API key per user (with scopes) for agents.
- REST API with Swagger + agent-friendly endpoints (bulk create, idempotency).
- Audit log (who/which agent did what).

## Out of scope (for now)

- Schedule/Gantt and **people allocation** (a leadership decision, not a tool's).
- Time tracking / hour logging.
- Formal sprints/cycles (may come later as an optional view).
- Billing.
- Real-time collaboration (websockets) — left for a later phase.

## Name (decided)

**Agentic Dev Maestro** — repo `agentic-dev-maestro`.

- **Agentic** — the AI agents act with autonomy (it's not bolted-on automation).
- **Dev** — the domain is development work (tasks, docs, board).
- **Maestro** — orchestrates the mixed team (humans + agents) around the work.

Day to day and in the documentation, the short name is **Maestro** (hence "Maestro Loop",
"Maestro API", etc.).
