// Tipos do domínio Agentic Dev Maestro (espelham as respostas da API).

export interface Company {
  id: number;
  name: string;
  slug: string;
  memberships?: { role: string }[];
}

export interface Project {
  id: number;
  name: string;
  key: string;
  description?: string;
}

export interface TaskAssignee {
  id: number;
  firstName: string;
  lastName: string;
}

export type TaskType = 'FEATURE' | 'BUG' | 'TECH_DEBT' | 'IMPROVEMENT' | 'CHORE';
export type CommentType = 'COMMENT' | 'CODE_REVIEW' | 'COMMIT_REF' | 'DEPLOY_LOG';

export interface ChecklistItem {
  id: number;
  title: string;
  checked: boolean;
  sortOrder: number;
}

export interface TaskDep {
  id: number;
  code: string;
  title: string;
  status: string;
  isDone?: boolean;
}

export interface Task {
  id: number;
  number: number;
  code: string;
  title: string;
  description?: string;
  objective?: string;
  acceptance?: string;
  status: string;
  type?: TaskType;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
  estimateMd?: number;
  columnId: number;
  projectId: number;
  parentId?: number;
  assigneeId?: number;
  assignee?: TaskAssignee | null;
  labels?: Label[];
  checklist?: ChecklistItem[];
  blockedBy?: { id: number; blockerId: number; blocker: { id: number; number: number; title: string; project: { key: string } } }[];
  blocking?: { id: number; blockedId: number; blocked: { id: number; number: number; title: string; project: { key: string } } }[];
}

export interface BoardColumn {
  id: number;
  name: string;
  order: number;
  wipLimit?: number;
  isDone: boolean;
  tasks: Task[];
}

export interface Board {
  id: number;
  name: string;
  columns: BoardColumn[];
}

export interface FlowNode {
  id: string;
  kind?: 'entry' | 'exit';
  code?: string;
  title?: string;
  status?: string;
  state?: 'todo' | 'doing' | 'blocked' | 'done';
  label?: string;
}

export interface FlowEdge {
  from: string;
  to: string;
}

export interface TaskFlow {
  task: { code: string; title: string; objective?: string; acceptance?: string };
  progress: { done: number; total: number };
  nodes: FlowNode[];
  edges: FlowEdge[];
}

export interface Label {
  id: number;
  name: string;
  color?: string;
}

export interface DocItem {
  id: number;
  title: string;
  body: string;
  type: 'SPEC' | 'PLAN' | 'NOTES' | 'ADR' | 'OTHER';
  version: number;
  projectId?: number;
  taskId?: number;
  updatedAt?: string;
}

export interface Comment {
  id: number;
  body: string;
  type?: CommentType;
  createdAt: string;
  viaApiKeyId?: number | null;
  author?: { id: number; firstName: string; lastName: string };
}

export interface MetricsSummary {
  totalTasks: number;
  doneTasks: number;
  completedLast7d: number;
  completedLast30d: number;
  avgLeadTimeHours: number | null;
  avgCycleTimeHours: number | null;
}

export interface MetricsResponse {
  summary: MetricsSummary;
  weeklyThroughput: { week: string; count: number }[];
  byType: Record<string, { total: number; done: number }>;
  byPriority: Record<string, { total: number; done: number }>;
  perProject: { id: number; name: string; key: string; total: number; done: number; percent: number }[];
}

export interface Member {
  id: number;
  role: string;
  user: { id: number; firstName: string; lastName: string; email: string };
}

export interface Invitation {
  id: number;
  email: string;
  role: string;
  expiresAt: string;
  createdAt: string;
}

// Resultado de convidar: 'added' (já tinha conta → virou membro) ou 'invited' (link enviado).
export interface InviteResult {
  mode: 'added' | 'invited';
  membership?: Member;
  invitation?: Invitation;
  link?: string;
}

export interface InvitationDetails {
  email: string;
  role: string;
  company: string;
  expiresAt: string;
}

export interface AcceptResult {
  companyId: number;
  role: string;
  alreadyMember: boolean;
}

export interface ApiKeyInfo {
  id: number;
  label: string;
  prefix: string;
  scopes?: string[];
  lastUsedAt?: string;
  expiresAt?: string;
  createdAt: string;
  secret?: string; // só presente na criação
}

export interface ActivityItem {
  id: number;
  entityType: string;
  entityId: number;
  action: string;
  viaApiKeyId?: number | null;
  createdAt: string;
  changes?: Record<string, unknown> | null;
}
