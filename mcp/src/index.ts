#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

// ---------------------------------------------------------------------------
// Configuration (via environment variables)
// ---------------------------------------------------------------------------
const API_URL = (process.env.MAESTRO_API_URL ?? "http://localhost:5000/api").replace(/\/$/, "");
const API_KEY = process.env.MAESTRO_API_KEY;

if (!API_KEY) {
  console.error(
    "[agentic-dev-maestro-mcp] FATAL: MAESTRO_API_KEY environment variable is required."
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
      `Maestro API ${method} ${path} failed: ${res.status} ${res.statusText} - ${text}`
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
  name: "agentic-dev-maestro",
  version: "0.1.0",
});

// --- Projects ---------------------------------------------------------------
server.registerTool(
  "maestro_list_projects",
  {
    description: "List all projects (boards) on the company server.",
    inputSchema: {},
  },
  async () => ok(await api("GET", "/projects"))
);

server.registerTool(
  "maestro_create_project",
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
  "maestro_get_board",
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
  "maestro_list_tasks",
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
  "maestro_get_task",
  {
    description: "Get a single task by its code (or id).",
    inputSchema: {
      code: z.string().describe("Task code, e.g. 'GAV-12'."),
    },
  },
  async ({ code }) => ok(await api("GET", `/tasks/${encodeURIComponent(code)}`))
);

server.registerTool(
  "maestro_create_task",
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
  "maestro_decompose",
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
  "maestro_move_task",
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
  "maestro_get_flow",
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

// --- Documents --------------------------------------------------------------
server.registerTool(
  "maestro_write_doc",
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
  "maestro_comment",
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
  console.error("[agentic-dev-maestro-mcp] connected via stdio. API:", API_URL);
}

main().catch((err) => {
  console.error("[agentic-dev-maestro-mcp] fatal:", err);
  process.exit(1);
});
