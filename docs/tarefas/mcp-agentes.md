> 🇧🇷 [Versão em português](mcp-agentes.ptbr.md)

# Tasks — MCP / Agents

A separate package that exposes the Maestro API as an **MCP server**, so agents
(Claude Code, etc.) can operate the boards natively. Design details in
[doc 03](../03-api-e-agentes.md#servidor-mcp-envólucro-da-api). Effort in man-days (md).

---

## M1 — MCP server scaffold · 1.5 md
- [ ] `maestro-mcp` package (Node/TypeScript) using the MCP SDK
- [ ] Config via env: `MAESTRO_API_URL`, `MAESTRO_API_KEY`, `MAESTRO_COMPANY_ID`
- [ ] Typed HTTP client (reuse the types generated from Swagger)
- [ ] Map API errors → MCP errors readable by the agent

## M2 — Read tools · 1 md
- [ ] `maestro_list_projects`
- [ ] `maestro_list_tasks` (filters: status, assignee, label)
- [ ] `maestro_get_task` (by `GAV-42` code)

## M3 — Write tools · 2 md
- [ ] `maestro_write_doc` (creates/updates a markdown doc on a project/task)
- [ ] `maestro_decompose` (bulk: tasks + subtasks, with `Idempotency-Key`)
- [ ] `maestro_move_task` (changes status on the board)
- [ ] `maestro_comment` (comments on a task)

## M4 — Packaging and usage · 1.5 md
- [ ] Publish/run via `npx` or a binary
- [ ] Example config in the MCP client (e.g., `claude` / `mcpServers`)
- [ ] Guide: "how to give an agent an API key and wire up the MCP"
- [ ] Least-privilege principle: recommend a key with minimal scopes

## M5 — End-to-end validation · 1 md
- [ ] Run the full **Maestro Loop** via MCP with a real agent
      (briefing → doc → decompose → move status)
- [ ] Verify that every action appears in the `ActivityLog` as "via agent"

---

## Quality checklist (MCP)

- [ ] Tools with clear descriptions and validated input schemas
- [ ] API errors reach the agent in an actionable form (missing field, scope)
- [ ] Idempotency honored in `decompose` (no duplicated tasks)
- [ ] Correct auditing (actions attributed to the agent's identity)
- [ ] Configuration guide tested by someone who did not write the code
