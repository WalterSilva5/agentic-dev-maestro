import axios from 'axios'

// Em dev o proxy do vite manda /api -> 9777; em prod a FastAPI serve tudo na mesma origem.
export const api = axios.create({ baseURL: '/api' })

// Workspaces
export const getWorkspaces = () => api.get('/workspaces').then((r) => r.data)
export const setActiveWorkspace = (id) => api.post('/workspaces/active', { id }).then((r) => r.data)
export const createWorkspace = (body) => api.post('/workspaces', body).then((r) => r.data)

// Projetos / board
export const getProjects = () => api.get('/projects').then((r) => r.data)
export const createProject = (body) => api.post('/projects', body).then((r) => r.data)
export const updateProject = (id, body) => api.patch(`/projects/${id}`, body).then((r) => r.data)
export const deleteProject = (id) => api.delete(`/projects/${id}`).then((r) => r.data)
export const moveProject = (id, targetWorkspaceId) => api.post(`/projects/${id}/move`, { targetWorkspaceId }).then((r) => r.data)
export const getBoard = (projectId, sprintId) =>
  api
    .get(`/projects/${projectId}/board`, { params: sprintId != null ? { sprintId } : {} })
    .then((r) => r.data)

// Tarefas
export const getTask = (code) => api.get(`/tasks/${code}`).then((r) => r.data)
export const createTask = (body) => api.post('/tasks', body).then((r) => r.data)
export const updateTask = (code, body) => api.patch(`/tasks/${code}`, body).then((r) => r.data)
export const moveTask = (code, columnId) => api.post(`/tasks/${code}/move`, { columnId }).then((r) => r.data)
export const archiveTask = (code) => api.post(`/tasks/${code}/archive`).then((r) => r.data)
export const unarchiveTask = (code) => api.post(`/tasks/${code}/unarchive`).then((r) => r.data)
export const getArchived = (projectId) => api.get(`/projects/${projectId}/archived`).then((r) => r.data)

// Sprints
export const getSprints = (projectId) => api.get(`/projects/${projectId}/sprints`).then((r) => r.data)
export const createSprint = (projectId, body) =>
  api.post(`/projects/${projectId}/sprints`, body).then((r) => r.data)
export const updateSprint = (id, body) => api.patch(`/sprints/${id}`, body).then((r) => r.data)
export const completeSprint = (id, body) =>
  api.post(`/sprints/${id}/complete`, body || {}).then((r) => r.data)
export const deleteSprint = (id) => api.delete(`/sprints/${id}`).then((r) => r.data)
export const getSprintRetro = (id) => api.get(`/sprints/${id}/retrospective`).then((r) => r.data)
export const generateSprintRetro = (id) => api.post(`/sprints/${id}/retrospective`).then((r) => r.data)
export const createRetroActions = (id, titles) =>
  api.post(`/sprints/${id}/retrospective/actions`, { titles }).then((r) => r.data)

// Checklist
export const addChecklist = (code, title) => api.post(`/tasks/${code}/checklist`, { title }).then((r) => r.data)
export const toggleChecklist = (id) => api.patch(`/tasks/checklist/${id}/toggle`).then((r) => r.data)
export const deleteChecklist = (id) => api.delete(`/tasks/checklist/${id}`).then((r) => r.data)

// Comentários
export const getComments = (taskId) => api.get('/comments', { params: { taskId } }).then((r) => r.data)
export const addComment = (taskId, body, type = 'COMMENT') =>
  api.post('/comments', { taskId, body, type }).then((r) => r.data)

// Labels
export const getLabels = () => api.get('/labels').then((r) => r.data)
export const createLabel = (name, color) => api.post('/labels', { name, color }).then((r) => r.data)
export const deleteLabel = (id) => api.delete(`/labels/${id}`).then((r) => r.data)

// TODOs
export const getTodos = () => api.get('/todos').then((r) => r.data)
export const addTodo = (body) =>
  api.post('/todos', typeof body === 'string' ? { text: body } : body).then((r) => r.data)
export const updateTodo = (id, body) => api.patch(`/todos/${id}`, body).then((r) => r.data)
export const deleteTodo = (id) => api.delete(`/todos/${id}`).then((r) => r.data)
export const getPendingTodos = () => api.get('/todos/pending').then((r) => r.data)
export const snoozeTodo = (id, minutes = 10) =>
  api.post(`/todos/${id}/snooze`, { minutes }).then((r) => r.data)

// Estudos
export const getStudyPlans = () => api.get('/study/plans').then((r) => r.data)
export const createStudyPlan = (body) => api.post('/study/plans', body).then((r) => r.data)
export const getStudyPlan = (id) => api.get(`/study/plans/${id}`).then((r) => r.data)
export const getTopics = (planId) => api.get(`/study/plans/${planId}/topics`).then((r) => r.data)
export const addTopic = (planId, body) => api.post(`/study/plans/${planId}/topics`, body).then((r) => r.data)
export const updateTopic = (id, body) => api.patch(`/study/topics/${id}`, body).then((r) => r.data)
export const studyAssistant = (body) => api.post('/study/assistant', body).then((r) => r.data)
export const createStudyPlanWithFiles = ({ title, category, description = '', files = [] }) => {
  const fd = new FormData()
  fd.append('title', title)
  fd.append('category', category)
  if (description) fd.append('description', description)
  for (const f of files) fd.append('files', f)
  return api.post('/study/plans/with-files', fd).then((r) => r.data)
}

// Meu Dia
export const getDaily = (date) => api.get(`/daily/${date}`).then((r) => r.data)
export const saveDaily = (date, body) => api.put(`/daily/${date}`, { body }).then((r) => r.data)
export const genDailyReport = (date) => api.post(`/daily/${date}/report`).then((r) => r.data)
export const getDailyActivity = (date) => api.get(`/daily/${date}/activity`).then((r) => r.data)

// Dashboard / métricas / atividade
export const getMetrics = () => api.get('/projects/metrics').then((r) => r.data)
// Relatório de métricas do projeto em PDF
export const metricsPdfUrl = (projectId) => `/api/projects/${projectId}/metrics/export.pdf`
export const getMetricsDimensions = (projectId) =>
  api.get(`/projects/${projectId}/metrics/dimensions`).then((r) => r.data)
export const getMetricsStages = (projectId) =>
  api.get(`/projects/${projectId}/metrics/stages`).then((r) => r.data)
export const getActivity = (limit = 15) => api.get('/activity', { params: { limit } }).then((r) => r.data)

// Assistente
export const assistantChat = (messages) => api.post('/assistant/chat', { messages }).then((r) => r.data)

// Configurações
export const getSettings = () => api.get('/settings').then((r) => r.data)
export const updateSettings = (body) => api.put('/settings', body).then((r) => r.data)

// Biblioteca — snippets & prompts
export const getSnippets = (params = {}) => api.get('/snippets', { params }).then((r) => r.data)
export const createSnippet = (body) => api.post('/snippets', body).then((r) => r.data)
export const updateSnippet = (id, body) => api.put(`/snippets/${id}`, body).then((r) => r.data)
export const useSnippet = (id) => api.post(`/snippets/${id}/use`).then((r) => r.data)
export const deleteSnippet = (id) => api.delete(`/snippets/${id}`).then((r) => r.data)

// Biblioteca — runbooks / comandos
export const getRunbooks = (params = {}) => api.get('/runbooks', { params }).then((r) => r.data)
export const createRunbook = (body) => api.post('/runbooks', body).then((r) => r.data)
export const updateRunbook = (id, body) => api.put(`/runbooks/${id}`, body).then((r) => r.data)
export const useRunbook = (id) => api.post(`/runbooks/${id}/use`).then((r) => r.data)
export const deleteRunbook = (id) => api.delete(`/runbooks/${id}`).then((r) => r.data)

// Importar TODO/FIXME do código
export const scanTodos = (body) => api.post('/code/scan-todos', body).then((r) => r.data)
export const importTodos = (body) => api.post('/code/import-todos', body).then((r) => r.data)

// Triagem de bugs
export const triageBug = (body) => api.post('/bugs/triage', body).then((r) => r.data)

// Code review assistant
export const codeReview = (body) => api.post('/code/review', body).then((r) => r.data)

// Cockpit de Git/PR
export const gitStatus = (path, prs = true) =>
  api.get('/git/status', { params: { path, prs } }).then((r) => r.data)

// Time tracking
export const getTimeLogs = (limit = 50) => api.get('/timelogs', { params: { limit } }).then((r) => r.data)
export const logTime = (body) => api.post('/timelogs', body).then((r) => r.data)
export const deleteTimeLog = (id) => api.delete(`/timelogs/${id}`).then((r) => r.data)

// Testador de API (mini-Postman)
export const getApiRequests = (params = {}) => api.get('/http-requests', { params }).then((r) => r.data)
export const createApiRequest = (body) => api.post('/http-requests', body).then((r) => r.data)
export const updateApiRequest = (id, body) => api.put(`/http-requests/${id}`, body).then((r) => r.data)
export const deleteApiRequest = (id) => api.delete(`/http-requests/${id}`).then((r) => r.data)
export const runApiRequest = (body) => api.post('/http-requests/run', body).then((r) => r.data)
export const getApiHistory = (params = {}) => api.get('/http-requests/history', { params }).then((r) => r.data)

// Digest proativo (standup)
export const getDigest = (days = 1) => api.get('/digest', { params: { days } }).then((r) => r.data)

// Coach proativo (dicas do agente ao longo do dia)
export const getCoachTip = () => api.get('/coach/tip').then((r) => r.data)
export const getCoachConfig = () => api.get('/coach/config').then((r) => r.data)
export const putCoachConfig = (body) => api.put('/coach/config', body).then((r) => r.data)

// Tradutor
export const translateText = (body) => api.post('/translate', body).then((r) => r.data)

// Base de conhecimento (2º cérebro)
export const getKbNotes = (params = {}) => api.get('/kb/notes', { params }).then((r) => r.data)
export const createKbNote = (body) => api.post('/documents', { ...body, type: 'KB' }).then((r) => r.data)
export const updateKbNote = (id, body) => api.put(`/documents/${id}`, body).then((r) => r.data)
export const deleteKbNote = (id) => api.delete(`/documents/${id}`).then((r) => r.data)
export const kbAsk = (body) => api.post('/kb/ask', body).then((r) => r.data)

// Épicos (agrupadores temáticos de cards)
export const getEpics = (projectId) => api.get(`/projects/${projectId}/epics`).then((r) => r.data)
export const createEpic = (projectId, body) => api.post(`/projects/${projectId}/epics`, body).then((r) => r.data)
export const updateEpic = (id, body) => api.patch(`/epics/${id}`, body).then((r) => r.data)
export const deleteEpic = (id) => api.delete(`/epics/${id}`).then((r) => r.data)
export const attachEpic = (epicId, taskId) => api.post(`/epics/${epicId}/tasks/${taskId}`).then((r) => r.data)
export const detachEpic = (epicId, taskId) => api.delete(`/epics/${epicId}/tasks/${taskId}`).then((r) => r.data)

// Goals (objetivos com progresso e contagem regressiva)
export const getGoals = (projectId) => api.get(`/projects/${projectId}/goals`).then((r) => r.data)
export const createGoal = (projectId, body) => api.post(`/projects/${projectId}/goals`, body).then((r) => r.data)
export const getGoal = (id) => api.get(`/goals/${id}`).then((r) => r.data)
export const updateGoal = (id, body) => api.patch(`/goals/${id}`, body).then((r) => r.data)
export const deleteGoal = (id) => api.delete(`/goals/${id}`).then((r) => r.data)

// Responsáveis (membros do projeto + métricas por pessoa)
export const getMembers = (projectId) => api.get(`/projects/${projectId}/members`).then((r) => r.data)
export const createMember = (projectId, body) => api.post(`/projects/${projectId}/members`, body).then((r) => r.data)
export const deleteMember = (id) => api.delete(`/members/${id}`).then((r) => r.data)

// Atalhos / links do projeto
export const getLinks = (projectId) => api.get(`/projects/${projectId}/links`).then((r) => r.data)
export const createLink = (projectId, body) => api.post(`/projects/${projectId}/links`, body).then((r) => r.data)
export const updateLink = (id, body) => api.patch(`/links/${id}`, body).then((r) => r.data)
export const deleteLink = (id) => api.delete(`/links/${id}`).then((r) => r.data)
export const reorderLinks = (projectId, orderedIds) => api.post(`/projects/${projectId}/links/reorder`, { orderedIds }).then((r) => r.data)

// Daily do projeto (registro de trabalho por dia)
export const getProjectDaily = (projectId, params = {}) =>
  api.get(`/projects/${projectId}/daily`, { params }).then((r) => r.data)
export const createProjectDaily = (projectId, body) =>
  api.post(`/projects/${projectId}/daily`, body).then((r) => r.data)
export const getProjectDailyEntry = (id) => api.get(`/project-daily/${id}`).then((r) => r.data)
export const updateProjectDaily = (id, body) => api.patch(`/project-daily/${id}`, body).then((r) => r.data)
export const deleteProjectDaily = (id) => api.delete(`/project-daily/${id}`).then((r) => r.data)
export const getProjectDailySummary = (projectId, params = {}) =>
  api.get(`/projects/${projectId}/daily/summary`, { params }).then((r) => r.data)
export const exportProjectDaily = (projectId, date) =>
  api.get(`/projects/${projectId}/daily/export`, { params: { date } }).then((r) => r.data)
export const importProjectDaily = (projectId, body) =>
  api.post(`/projects/${projectId}/daily/import`, body).then((r) => r.data)

export const getHealth = () => api.get('/health').then((r) => r.data)

// Reuniões (gravações do app desktop)
export const listRecordings = (params) => api.get('/recordings', { params }).then((r) => r.data)
export const getRecording = (id) => api.get(`/recordings/${id}`).then((r) => r.data)
export const updateRecording = (id, body) => api.patch(`/recordings/${id}`, body).then((r) => r.data)
export const deleteRecording = (id) => api.delete(`/recordings/${id}`).then((r) => r.data)
export const archiveRecording = (id, archived) => api.post(`/recordings/${id}/archive`, { archived }).then((r) => r.data)
export const recordingExportUrl = (id, format = 'md') => `/api/recordings/${id}/export?format=${format}`
export const recordingAudioUrl = (id) => `/api/recordings/${id}/audio`

// Backup do banco
export const createBackup = (all = false) =>
  api.post('/backup', null, { params: all ? { all: 1 } : {} }).then((r) => r.data)
export const listBackups = () => api.get('/backup').then((r) => r.data)
export const backupDownloadUrl = (file) => `/api/backup/${encodeURIComponent(file)}`

// Time — report semanal por membro
export const getTeamWeekly = (projectId, week) =>
  api.get(`/projects/${projectId}/team/weekly`, { params: week ? { week } : {} }).then((r) => r.data)
export const saveTeamNote = (projectId, body) =>
  api.put(`/projects/${projectId}/team/notes`, body).then((r) => r.data)
export const teamReportUrl = (projectId, week, anonymized = false) => {
  const p = new URLSearchParams()
  if (week) p.set('week', week)
  if (anonymized) p.set('anonymized', '1')
  return `/api/projects/${projectId}/team/weekly/export?${p.toString()}`
}
