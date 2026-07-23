import { tool } from "@opencode-ai/plugin";

const API_URL = process.env.MAESTRO_API_URL || "http://localhost:5000/api";
const API_KEY = process.env.MAESTRO_API_KEY || "";

function getHeaders() {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (API_KEY) headers["x-api-key"] = API_KEY;
  return headers;
}

async function api(path: string, options: { method?: string; body?: unknown } = {}) {
  const url = `${API_URL}${path}`;
  const res = await fetch(url, {
    method: options.method || "GET",
    headers: getHeaders(),
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      const json = JSON.parse(text);
      detail = json.message || json.messages?.join("; ") || text;
    } catch {}
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return res.json();
}

// ----------------------------------------------------------------
// Projetos
// ----------------------------------------------------------------

export const listProjects = tool({
  description: "Lista todos os projetos disponíveis no workspace.",
  args: {},
  async execute() {
    return api("/projects");
  },
});

export const board = tool({
  description:
    "Retorna o quadro kanban (board) de um projeto com todas as colunas e tarefas. " +
    "Use esta ferramenta para ver o estado atual de cada coluna (Backlog, A fazer, Fazendo, etc.) " +
    "e quais tarefas estão em cada uma.",
  args: {
    projectId: tool.schema
      .number()
      .describe("ID numérico do projeto (ex: 2 para MAESTRO)"),
  },
  async execute(args) {
    return api(`/projects/${args.projectId}/board`);
  },
});

// ----------------------------------------------------------------
// Tarefas
// ----------------------------------------------------------------

export const getTask = tool({
  description:
    "Retorna os detalhes completos de uma tarefa pelo código (ex: MAESTRO-10) ou ID numérico.",
  args: {
    idOrCode: tool.schema
      .string()
      .describe("Código da tarefa (ex: MAESTRO-10) ou ID numérico"),
  },
  async execute(args) {
    return api(`/tasks/${args.idOrCode}`);
  },
});

export const listTasks = tool({
  description:
    "Lista tarefas com filtros opcionais. " +
    "Use projectId para filtrar por projeto, status para coluna, " +
    "parentId para listar subtarefas de uma tarefa específica.",
  args: {
    projectId: tool.schema
      .number()
      .optional()
      .describe("Filtrar por ID do projeto"),
    status: tool.schema
      .string()
      .optional()
      .describe("Filtrar por nome da coluna (Backlog, A fazer, Fazendo, Revisão, Concluído)"),
    assigneeId: tool.schema
      .number()
      .optional()
      .describe("Filtrar por ID do responsável"),
    priority: tool.schema
      .string()
      .optional()
      .describe("Filtrar por prioridade (LOW, MEDIUM, HIGH, URGENT)"),
    parentId: tool.schema
      .number()
      .optional()
      .describe("Filtrar por tarefa pai (para listar subtarefas)"),
    search: tool.schema
      .string()
      .optional()
      .describe("Busca por texto no título"),
  },
  async execute(args) {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(args)) {
      if (v !== undefined && v !== null) params.set(k, String(v));
    }
    const qs = params.toString();
    return api(`/tasks${qs ? `?${qs}` : ""}`);
  },
});

export const createTask = tool({
  description:
    "Cria uma nova tarefa. Use projectId para o projeto, title obrigatório, " +
    "e opcionalmente description, objective, acceptance, priority, estimateMd, parentId (para subtarefa), " +
    "assigneeId. Se columnId não for informado, usa a primeira coluna do board.",
  args: {
    projectId: tool.schema.number().describe("ID do projeto"),
    title: tool.schema.string().describe("Título da tarefa"),
    description: tool.schema.string().optional().describe("Descrição em markdown"),
    objective: tool.schema.string().optional().describe("Objetivo da tarefa"),
    acceptance: tool.schema.string().optional().describe("Critério de aceite"),
    priority: tool.schema
      .string()
      .optional()
      .describe("Prioridade: LOW, MEDIUM (padrão), HIGH, URGENT"),
    estimateMd: tool.schema
      .number()
      .optional()
      .describe("Estimativa em homem-dia"),
    columnId: tool.schema
      .number()
      .optional()
      .describe("ID da coluna (se vazio, usa a primeira)"),
    parentId: tool.schema
      .number()
      .optional()
      .describe("ID da tarefa pai (para criar subtarefa)"),
    assigneeId: tool.schema
      .number()
      .optional()
      .describe("ID do usuário responsável"),
  },
  async execute(args) {
    return api("/tasks", { method: "POST", body: args });
  },
});

export const updateTask = tool({
  description:
    "Atualiza campos de uma tarefa existente. " +
    "Envie apenas os campos que deseja modificar (parcial).",
  args: {
    idOrCode: tool.schema
      .string()
      .describe("Código da tarefa (ex: MAESTRO-10) ou ID numérico"),
    title: tool.schema.string().optional().describe("Novo título"),
    description: tool.schema.string().optional().describe("Nova descrição"),
    objective: tool.schema.string().optional().describe("Novo objetivo"),
    acceptance: tool.schema.string().optional().describe("Novo critério de aceite"),
    priority: tool.schema
      .string()
      .optional()
      .describe("Nova prioridade: LOW, MEDIUM, HIGH, URGENT"),
    estimateMd: tool.schema
      .number()
      .optional()
      .describe("Nova estimativa em homem-dia"),
    assigneeId: tool.schema
      .number()
      .optional()
      .describe("Novo ID do responsável"),
  },
  async execute(args) {
    const { idOrCode, ...body } = args;
    return api(`/tasks/${idOrCode}`, { method: "PATCH", body });
  },
});

export const moveTask = tool({
  description:
    "Move uma tarefa para outra coluna do board. " +
    "Use esta ferramenta para avançar tarefas no fluxo (ex: de 'Fazendo' para 'Revisão').",
  args: {
    idOrCode: tool.schema
      .string()
      .describe("Código da tarefa (ex: MAESTRO-10) ou ID numérico"),
    columnId: tool.schema.number().describe("ID da coluna de destino"),
  },
  async execute(args) {
    const { idOrCode, columnId } = args;
    return api(`/tasks/${idOrCode}/move`, {
      method: "POST",
      body: { columnId },
    });
  },
});

export const deleteTask = tool({
  description:
    "Exclui (soft delete) uma tarefa pelo código ou ID. A tarefa não é removida " +
    "do banco, apenas marcada como deletada.",
  args: {
    idOrCode: tool.schema
      .string()
      .describe("Código da tarefa (ex: MAESTRO-10) ou ID numérico"),
  },
  async execute(args) {
    return api(`/tasks/${args.idOrCode}`, { method: "DELETE" });
  },
});

// ----------------------------------------------------------------
// Subtarefas (atalho: cria task com parentId)
// ----------------------------------------------------------------

export const addSubtask = tool({
  description:
    "Adiciona uma subtarefa a uma tarefa principal. Subtarefas têm apenas título " +
    "(sem descrição). Use esta ferramenta para decompor tarefas grandes.",
  args: {
    parentCode: tool.schema
      .string()
      .describe("Código da tarefa pai (ex: MAESTRO-10)"),
    title: tool.schema.string().describe("Título da subtarefa"),
    projectId: tool.schema
      .number()
      .optional()
      .describe("ID do projeto (opcional, resolvido automaticamente da tarefa pai)"),
  },
  async execute(args) {
    if (args.projectId) {
      return api("/tasks", {
        method: "POST",
        body: {
          projectId: args.projectId,
          title: args.title,
          parentId: args.parentCode,
        },
      });
    }
    // Resolve o projectId da tarefa pai
    const parent = await api(`/tasks/${args.parentCode}`);
    return api("/tasks", {
      method: "POST",
      body: {
        projectId: parent.projectId,
        title: args.title,
        parentId: parent.id,
      },
    });
  },
});

// ----------------------------------------------------------------
// Comentários
// ----------------------------------------------------------------

export const addComment = tool({
  description:
    "Adiciona um comentário a uma tarefa. Suporta markdown, blocos de código, " +
    "listas, etc. Use para postar code reviews, mensagens de commit, " +
    "atualizações de progresso ou qualquer comunicação sobre a tarefa.",
  args: {
    taskId: tool.schema.number().describe("ID numérico da tarefa"),
    body: tool.schema
      .string()
      .describe(
        "Corpo do comentário em markdown. Para code review, use ```linguagem ... ```. " +
          "Para commits, use formatação de mensagem de commit."
      ),
  },
  async execute(args) {
    return api("/comments", { method: "POST", body: args });
  },
});

// ----------------------------------------------------------------
// Fluxo
// ----------------------------------------------------------------

export const getFlow = tool({
  description:
    "Retorna o grafo de fluxo de uma tarefa: objetivo -> subtarefas -> aceite. " +
    "Use format='mermaid' para obter o diagrama em formato Mermaid.js " +
    "(útil para embed em documentação ou visualização).",
  args: {
    idOrCode: tool.schema
      .string()
      .describe("Código da tarefa (ex: MAESTRO-10) ou ID numérico"),
    format: tool.schema
      .string()
      .optional()
      .describe("Formato de saída: 'mermaid' para diagrama Mermaid"),
  },
  async execute(args) {
    const qs = args.format ? `?format=${args.format}` : "";
    return api(`/tasks/${args.idOrCode}/flow${qs}`);
  },
});

// ----------------------------------------------------------------
// Documentos
// ----------------------------------------------------------------

export const createDocument = tool({
  description:
    "Cria um novo documento associado a um projeto ou tarefa. " +
    "Tipos disponíveis: SPEC (especificação), PLAN (plano), NOTES (notas), " +
    "ADR (Architecture Decision Record), OTHER (outro). " +
    "O corpo do documento aceita markdown completo.",
  args: {
    title: tool.schema.string().describe("Título do documento"),
    body: tool.schema.string().optional().describe("Conteúdo em markdown"),
    type: tool.schema
      .string()
      .optional()
      .describe("Tipo: SPEC, PLAN, NOTES, ADR, OTHER (padrão: NOTES)"),
    projectId: tool.schema
      .number()
      .optional()
      .describe("ID do projeto (opcional)"),
    taskId: tool.schema
      .number()
      .optional()
      .describe("ID da tarefa (opcional)"),
  },
  async execute(args) {
    return api("/documents", { method: "POST", body: args });
  },
});

// ----------------------------------------------------------------
// Memória agentic (workspace)
// ----------------------------------------------------------------

export const searchMemory = tool({
  description:
    "Busca híbrida (semântica + keywords) na memória agentic do workspace. " +
    "Retorna fatos, decisões, preferências, episódios e procedimentos relevantes, " +
    "com agentContext em markdown pronto para o agente. Use no início de sessões " +
    "e sempre que precisar de contexto histórico do projeto.",
  args: {
    query: tool.schema.string().describe("Consulta em linguagem natural"),
    kind: tool.schema
      .string()
      .optional()
      .describe(
        "Filtro: fact|decision|preference|episode|procedure|context (vírgula para vários)"
      ),
    projectId: tool.schema.number().optional().describe("Filtrar por projeto"),
    taskId: tool.schema.number().optional().describe("Filtrar por tarefa"),
    topK: tool.schema.number().optional().describe("Máximo de resultados (padrão 8)"),
  },
  async execute(args) {
    return api("/memory/search", {
      method: "POST",
      body: {
        query: args.query,
        kind: args.kind,
        projectId: args.projectId,
        taskId: args.taskId,
        topK: args.topK,
      },
    });
  },
});

export const remember = tool({
  description:
    "Grava uma memória duradoura no workspace ativo para uso futuro por agentes. " +
    "Kinds: fact, decision, preference, episode, procedure, context. " +
    "Use para decisões de arquitetura, preferências, lições aprendidas e contexto.",
  args: {
    title: tool.schema.string().describe("Título curto e legível"),
    content: tool.schema.string().describe("Conteúdo completo da memória"),
    kind: tool.schema
      .string()
      .optional()
      .describe("fact|decision|preference|episode|procedure|context (padrão: fact)"),
    summary: tool.schema.string().optional().describe("Resumo curto opcional"),
    tags: tool.schema
      .string()
      .optional()
      .describe("Tags separadas por vírgula"),
    projectId: tool.schema.number().optional().describe("ID do projeto"),
    taskId: tool.schema.number().optional().describe("ID da tarefa"),
    importance: tool.schema
      .number()
      .optional()
      .describe("Importância 0.0–1.0 (padrão 0.5)"),
  },
  async execute(args) {
    const tags = args.tags
      ? args.tags.split(",").map((t: string) => t.trim()).filter(Boolean)
      : undefined;
    return api("/memory", {
      method: "POST",
      body: {
        title: args.title,
        content: args.content,
        kind: args.kind || "fact",
        summary: args.summary || "",
        tags,
        projectId: args.projectId,
        taskId: args.taskId,
        sourceType: "agent",
        importance: args.importance ?? 0.5,
      },
    });
  },
});

export const listMemory = tool({
  description:
    "Lista memórias do workspace com filtros opcionais (kind, projeto, tarefa, texto).",
  args: {
    q: tool.schema.string().optional().describe("Filtro de texto"),
    kind: tool.schema.string().optional().describe("fact|decision|preference|..."),
    projectId: tool.schema.number().optional().describe("ID do projeto"),
    taskId: tool.schema.number().optional().describe("ID da tarefa"),
    limit: tool.schema.number().optional().describe("Limite (padrão 50)"),
  },
  async execute(args) {
    const params = new URLSearchParams();
    if (args.q) params.set("q", args.q);
    if (args.kind) params.set("kind", args.kind);
    if (args.projectId != null) params.set("projectId", String(args.projectId));
    if (args.taskId != null) params.set("taskId", String(args.taskId));
    if (args.limit != null) params.set("limit", String(args.limit));
    const qs = params.toString();
    return api(`/memory${qs ? `?${qs}` : ""}`);
  },
});

export const ingestMemory = tool({
  description:
    "Ingere uma entidade existente na memória agentic (task, comment, document, " +
    "daily, recording, sprint, kb). Gera entradas estruturadas a partir da fonte.",
  args: {
    sourceType: tool.schema
      .string()
      .describe("task|comment|document|daily|recording|sprint|kb"),
    sourceId: tool.schema.number().describe("ID numérico da entidade fonte"),
    projectId: tool.schema.number().optional().describe("ID do projeto (opcional)"),
  },
  async execute(args) {
    return api("/memory/ingest", {
      method: "POST",
      body: {
        sourceType: args.sourceType,
        sourceId: args.sourceId,
        projectId: args.projectId,
      },
    });
  },
});
