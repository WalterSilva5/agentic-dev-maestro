#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

// ---------------------------------------------------------------------------
// Configuration (via environment variables)
// ---------------------------------------------------------------------------
const API_URL = (process.env.RELAY_API_URL ?? process.env.MAESTRO_API_URL ?? "http://localhost:5000/api").replace(/\/$/, "");
const API_KEY = process.env.RELAY_API_KEY ?? process.env.MAESTRO_API_KEY;

if (!API_KEY) {
  console.error(
    "[relay-mcp] FATAL: RELAY_API_KEY environment variable is required."
  );
  process.exit(1);
}

// ---------------------------------------------------------------------------
// HTTP helper
// ---------------------------------------------------------------------------
type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

async function api(
  method: HttpMethod,
  path: string,
  body?: unknown,
  extraHeaders?: Record<string, string>
): Promise<unknown> {
  const headers: Record<string, string> = {
    "x-api-key": API_KEY as string,
    "Content-Type": "application/json",
    ...extraHeaders,
  };

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  const text = await res.text();

  if (!res.ok) {
    throw new Error(
      `Relay API ${method} ${path} failed: ${res.status} ${res.statusText} - ${text}`
    );
  }

  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

// Wrap a JSON-serializable result in the MCP text-content shape.
function ok(result: unknown) {
  return {
    content: [
      {
        type: "text" as const,
        text: JSON.stringify(result, null, 2),
      },
    ],
  };
}

// Build a querystring from an object, skipping undefined/empty values.
function qs(params: Record<string, unknown>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    sp.append(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

// ---------------------------------------------------------------------------
// MCP server + tools
// ---------------------------------------------------------------------------
const server = new McpServer({
  name: "relay",
  version: "0.1.0",
});

// --- Projects ---------------------------------------------------------------
server.registerTool(
  "relay_list_projects",
  {
    description: "List all projects (boards) on the company server.",
    inputSchema: {},
  },
  async () => ok(await api("GET", "/projects"))
);

server.registerTool(
  "relay_create_project",
  {
    description: "Create a new project (board).",
    inputSchema: {
      name: z.string().describe("Project name."),
      key: z.string().describe("Short project key (e.g. 'GAV')."),
      description: z.string().optional().describe("Optional project description."),
    },
  },
  async ({ name, key, description }) =>
    ok(await api("POST", "/projects", { name, key, description }))
);

server.registerTool(
  "relay_get_board",
  {
    description: "Get the kanban board (columns + tasks) for a project.",
    inputSchema: {
      projectId: z.number().int().describe("Project id."),
    },
  },
  async ({ projectId }) => ok(await api("GET", `/projects/${projectId}/board`))
);

// --- Tasks ------------------------------------------------------------------
server.registerTool(
  "relay_list_tasks",
  {
    description: "List tasks, optionally filtered by project, status and/or free-text search.",
    inputSchema: {
      projectId: z.number().int().optional().describe("Filter by project id."),
      status: z.string().optional().describe("Filter by status."),
      search: z.string().optional().describe("Free-text search."),
    },
  },
  async ({ projectId, status, search }) =>
    ok(await api("GET", `/tasks${qs({ projectId, status, search })}`))
);

server.registerTool(
  "relay_get_task",
  {
    description: "Get a single task by its code (or id).",
    inputSchema: {
      code: z.string().describe("Task code, e.g. 'GAV-12'."),
    },
  },
  async ({ code }) => ok(await api("GET", `/tasks/${encodeURIComponent(code)}`))
);

server.registerTool(
  "relay_create_task",
  {
    description: "Create a single task in a project.",
    inputSchema: {
      projectId: z.number().int().describe("Project id."),
      title: z.string().describe("Task title."),
      objective: z.string().optional().describe("What the task should accomplish."),
      acceptance: z.string().optional().describe("Acceptance criteria."),
      priority: z
        .enum(["LOW", "MEDIUM", "HIGH", "URGENT"])
        .optional()
        .describe("Task priority."),
      estimateMd: z.number().optional().describe("Estimate in man-days."),
      columnId: z.number().int().optional().describe("Target column id on the board."),
    },
  },
  async (args) => ok(await api("POST", "/tasks", args))
);

const subtaskSchema = z.object({
  ref: z.string().optional().describe("Local reference id for cross-linking dependencies."),
  title: z.string(),
  estimateMd: z.number().optional(),
  dependsOn: z.array(z.string()).optional().describe("Refs of subtasks this one depends on."),
});

const itemSchema = z.object({
  ref: z.string().optional().describe("Local reference id for cross-linking."),
  title: z.string(),
  objective: z.string().optional(),
  acceptance: z.string().optional(),
  priority: z.string().optional(),
  subtasks: z.array(subtaskSchema).optional(),
});

server.registerTool(
  "relay_decompose",
  {
    description:
      "Bulk-create a decomposed plan: a set of tasks (items) each with optional subtasks and dependencies. Pass an idempotencyKey to make the operation safely retryable.",
    inputSchema: {
      projectId: z.number().int().describe("Project id."),
      items: z.array(itemSchema).describe("Tasks to create, each with optional subtasks."),
      idempotencyKey: z
        .string()
        .optional()
        .describe("Sent as the Idempotency-Key header to dedupe retries."),
    },
  },
  async ({ projectId, items, idempotencyKey }) => {
    const extra = idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined;
    return ok(await api("POST", "/tasks/bulk", { projectId, items }, extra));
  }
);

server.registerTool(
  "relay_move_task",
  {
    description: "Move a task to a different board column.",
    inputSchema: {
      code: z.string().describe("Task code, e.g. 'GAV-12'."),
      columnId: z.number().int().describe("Destination column id."),
    },
  },
  async ({ code, columnId }) =>
    ok(await api("POST", `/tasks/${encodeURIComponent(code)}/move`, { columnId }))
);

server.registerTool(
  "relay_get_flow",
  {
    description:
      "Get a task's flow (subtasks + dependency graph), as JSON or as a Mermaid diagram.",
    inputSchema: {
      code: z.string().describe("Task code, e.g. 'GAV-12'."),
      format: z
        .enum(["json", "mermaid"])
        .optional()
        .describe("Output format. Defaults to json."),
    },
  },
  async ({ code, format }) => {
    const suffix = format === "mermaid" ? "?format=mermaid" : "";
    return ok(await api("GET", `/tasks/${encodeURIComponent(code)}/flow${suffix}`));
  }
);

// --- Epics ------------------------------------------------------------------
server.registerTool(
  "relay_list_epics",
  {
    description: "List epics of a project.",
    inputSchema: {
      projectId: z.number().int().describe("Project id."),
    },
  },
  async ({ projectId }) => ok(await api("GET", `/projects/${projectId}/epics`))
);

server.registerTool(
  "relay_create_epic",
  {
    description: "Create an epic (thematic card group) in a project.",
    inputSchema: {
      projectId: z.number().int().describe("Project id."),
      name: z.string().describe("Epic name."),
      color: z.string().optional().describe("Hex color, e.g. '#6741D9'."),
    },
  },
  async ({ projectId, name, color }) =>
    ok(await api("POST", `/projects/${projectId}/epics`, { name, color }))
);

server.registerTool(
  "relay_link_epic",
  {
    description: "Attach a task to an epic, or detach it with unlink=true.",
    inputSchema: {
      epicId: z.number().int().describe("Epic id."),
      taskId: z.number().int().describe("Task id."),
      unlink: z.boolean().optional().describe("Detach instead of attach."),
    },
  },
  async ({ epicId, taskId, unlink }) =>
    ok(await api(unlink ? "DELETE" : "POST", `/epics/${epicId}/tasks/${taskId}`))
);

// --- Goals ------------------------------------------------------------------
server.registerTool(
  "relay_list_goals",
  {
    description: "List goals of a project, each with progress (total/done/pct/daysLeft).",
    inputSchema: {
      projectId: z.number().int().describe("Project id."),
    },
  },
  async ({ projectId }) => ok(await api("GET", `/projects/${projectId}/goals`))
);

server.registerTool(
  "relay_create_goal",
  {
    description: "Create a goal: deliver cards matching tag/epic/sprint filters by a due date.",
    inputSchema: {
      projectId: z.number().int().describe("Project id."),
      name: z.string().describe("Goal name."),
      dueDate: z.string().optional().describe("ISO date, e.g. '2026-12-31'."),
      tag: z.string().optional().describe("Only cards with this tag."),
      epicId: z.number().int().optional().describe("Only cards in this epic."),
      sprintId: z.number().int().optional().describe("Only cards in this sprint."),
    },
  },
  async (args) => {
    const { projectId, ...body } = args as { projectId: number } & Record<string, unknown>;
    return ok(await api("POST", `/projects/${projectId}/goals`, body));
  }
);

server.registerTool(
  "relay_goal_progress",
  {
    description: "Get a goal with its current progress (total/done/pct/daysLeft).",
    inputSchema: {
      goalId: z.number().int().describe("Goal id."),
    },
  },
  async ({ goalId }) => ok(await api("GET", `/goals/${goalId}`))
);

// --- Members ----------------------------------------------------------------
server.registerTool(
  "relay_list_members",
  {
    description: "List project assignees with per-person metrics (total/done/pct/overdue).",
    inputSchema: {
      projectId: z.number().int().describe("Project id."),
    },
  },
  async ({ projectId }) => ok(await api("GET", `/projects/${projectId}/members`))
);

server.registerTool(
  "relay_add_member",
  {
    description: "Add an assignee to a project (idempotent by name).",
    inputSchema: {
      projectId: z.number().int().describe("Project id."),
      name: z.string().describe("Assignee name."),
    },
  },
  async ({ projectId, name }) =>
    ok(await api("POST", `/projects/${projectId}/members`, { name }))
);

server.registerTool(
  "relay_assign_task",
  {
    description: "Assign a task to an assignee (creates the member if missing).",
    inputSchema: {
      code: z.string().describe("Task code, e.g. 'GAV-12'."),
      assignee: z.string().describe("Assignee name."),
    },
  },
  async ({ code, assignee }) =>
    ok(await api("PATCH", `/tasks/${encodeURIComponent(code)}`, { assignee }))
);

// --- Documents --------------------------------------------------------------
server.registerTool(
  "relay_write_doc",
  {
    description: "Create a document, optionally attached to a project or task.",
    inputSchema: {
      title: z.string().describe("Document title."),
      body: z.string().describe("Document body (markdown)."),
      type: z.string().optional().describe("Document type."),
      projectId: z.number().int().optional().describe("Attach to this project."),
      taskId: z.number().int().optional().describe("Attach to this task."),
    },
  },
  async (args) => ok(await api("POST", "/documents", args))
);

// --- Comments ---------------------------------------------------------------
server.registerTool(
  "relay_comment",
  {
    description: "Add a comment to a task.",
    inputSchema: {
      taskId: z.number().int().describe("Task id."),
      body: z.string().describe("Comment body."),
    },
  },
  async ({ taskId, body }) => ok(await api("POST", "/comments", { taskId, body }))
);

// ---------------------------------------------------------------------------
// Wire up stdio transport
// ---------------------------------------------------------------------------
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[relay-mcp] connected via stdio. API:", API_URL);
}

main().catch((err) => {
  console.error("[relay-mcp] fatal:", err);
  process.exit(1);
});
