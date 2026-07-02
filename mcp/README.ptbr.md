> 🇬🇧 [English version](README.md)

# agentic-dev-maestro-mcp

A standalone [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
wraps the **Agentic Dev Maestro** REST API. It lets AI agents (e.g. Claude Code, Claude
Desktop, Cursor) manage Maestro boards natively — listing projects, creating and moving
tasks, decomposing work into subtasks with dependencies, writing docs, and commenting.

It speaks MCP over **stdio** and talks to your Maestro backend over HTTP.

## Requirements

- Node.js 18+ (global `fetch` is required; tested on Node 22+).
- A running Agentic Dev Maestro backend.
- A Maestro API key (`adm_...`). The key is bound to a single company server-side, so the
  server never sends a company id — authentication is just the `x-api-key` header.

## Install & build

```bash
cd mcp
npm install
npm run build      # tsc -> dist/index.js
```

Run it directly (mostly for a smoke test — MCP clients launch it for you):

```bash
MAESTRO_API_KEY=adm_xxx npm start
```

## Configuration (environment variables)

| Variable           | Required | Default                      | Description                                   |
| ------------------ | -------- | ---------------------------- | --------------------------------------------- |
| `MAESTRO_API_URL`  | no       | `http://localhost:5000/api`  | Base URL of the Maestro REST API.             |
| `MAESTRO_API_KEY`  | **yes**  | —                            | API key sent as `x-api-key` on every request. |

If `MAESTRO_API_KEY` is missing, the server logs to stderr and exits with code 1.

## MCP client configuration

Add an entry pointing at the built `dist/index.js`. Example (`claude_desktop_config.json`,
Cursor `mcp.json`, or Claude Code `.mcp.json`):

```json
{
  "mcpServers": {
    "maestro": {
      "command": "node",
      "args": ["/abs/path/to/mcp/dist/index.js"],
      "env": {
        "MAESTRO_API_URL": "http://localhost:5000/api",
        "MAESTRO_API_KEY": "adm_..."
      }
    }
  }
}
```

For Claude Code you can also register it via CLI:

```bash
claude mcp add maestro \
  --env MAESTRO_API_URL=http://localhost:5000/api \
  --env MAESTRO_API_KEY=adm_... \
  -- node /abs/path/to/mcp/dist/index.js
```

## Tools

| Tool                     | REST call                              | Description                                            |
| ------------------------ | -------------------------------------- | ------------------------------------------------------ |
| `maestro_list_projects`  | `GET /projects`                        | List all projects.                                     |
| `maestro_create_project` | `POST /projects`                       | Create a project (`name`, `key`, `description?`).      |
| `maestro_get_board`      | `GET /projects/:projectId/board`       | Get the kanban board for a project.                    |
| `maestro_list_tasks`     | `GET /tasks?...`                       | List tasks (`projectId?`, `status?`, `search?`).       |
| `maestro_get_task`       | `GET /tasks/:code`                     | Get one task by code.                                  |
| `maestro_create_task`    | `POST /tasks`                          | Create a task.                                         |
| `maestro_decompose`      | `POST /tasks/bulk`                     | Bulk-create tasks + subtasks + dependencies.           |
| `maestro_move_task`      | `POST /tasks/:code/move`               | Move a task to another column.                         |
| `maestro_get_flow`       | `GET /tasks/:code/flow`                | Get the task flow as JSON or `format=mermaid`.         |
| `maestro_write_doc`      | `POST /documents`                      | Create a document.                                     |
| `maestro_comment`        | `POST /comments`                       | Comment on a task.                                     |

### `maestro_decompose` body shape

```jsonc
{
  "projectId": 1,
  "items": [
    {
      "ref": "epic-auth",
      "title": "Authentication",
      "objective": "Add login + sessions",
      "acceptance": "Users can log in and stay logged in",
      "priority": "HIGH",
      "subtasks": [
        { "ref": "login-ui", "title": "Login form" },
        { "ref": "login-api", "title": "Auth endpoint", "estimateMd": 2, "dependsOn": ["login-ui"] }
      ]
    }
  ],
  "idempotencyKey": "plan-2026-06-22"   // optional -> sent as Idempotency-Key header
}
```

Every tool returns the parsed JSON response from the Maestro API as text content.

## License

UNLICENSED — internal/private.
