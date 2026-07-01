import axios from 'axios'

// Em dev o proxy do vite manda /api -> 9777; em prod a FastAPI serve tudo na mesma origem.
export const api = axios.create({ baseURL: '/api' })

// Workspaces
export const getWorkspaces = () => api.get('/workspaces').then((r) => r.data)
export const setActiveWorkspace = (id) => api.post('/workspaces/active', { id }).then((r) => r.data)

// Projetos / board
export const getProjects = () => api.get('/projects').then((r) => r.data)
export const createProject = (body) => api.post('/projects', body).then((r) => r.data)
export const deleteProject = (id) => api.delete(`/projects/${id}`).then((r) => r.data)
export const getBoard = (projectId) => api.get(`/projects/${projectId}/board`).then((r) => r.data)

// Tarefas
export const getTask = (code) => api.get(`/tasks/${code}`).then((r) => r.data)
export const createTask = (body) => api.post('/tasks', body).then((r) => r.data)
export const updateTask = (code, body) => api.patch(`/tasks/${code}`, body).then((r) => r.data)
export const moveTask = (code, columnId) => api.post(`/tasks/${code}/move`, { columnId }).then((r) => r.data)

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
export const addTodo = (text) => api.post('/todos', { text }).then((r) => r.data)
export const updateTodo = (id, body) => api.patch(`/todos/${id}`, body).then((r) => r.data)
export const deleteTodo = (id) => api.delete(`/todos/${id}`).then((r) => r.data)

// Estudos
export const getStudyPlans = () => api.get('/study/plans').then((r) => r.data)
export const createStudyPlan = (body) => api.post('/study/plans', body).then((r) => r.data)
export const getStudyPlan = (id) => api.get(`/study/plans/${id}`).then((r) => r.data)
export const getTopics = (planId) => api.get(`/study/plans/${planId}/topics`).then((r) => r.data)
export const addTopic = (planId, body) => api.post(`/study/plans/${planId}/topics`, body).then((r) => r.data)
export const updateTopic = (id, body) => api.patch(`/study/topics/${id}`, body).then((r) => r.data)

// Meu Dia
export const getDaily = (date) => api.get(`/daily/${date}`).then((r) => r.data)
export const saveDaily = (date, body) => api.put(`/daily/${date}`, { body }).then((r) => r.data)
export const genDailyReport = (date) => api.post(`/daily/${date}/report`).then((r) => r.data)
export const getDailyActivity = (date) => api.get(`/daily/${date}/activity`).then((r) => r.data)

// Dashboard / métricas / atividade
export const getMetrics = () => api.get('/projects/metrics').then((r) => r.data)
export const getActivity = (limit = 15) => api.get('/activity', { params: { limit } }).then((r) => r.data)

// Assistente
export const assistantChat = (messages) => api.post('/assistant/chat', { messages }).then((r) => r.data)

// Configurações
export const getSettings = () => api.get('/settings').then((r) => r.data)
export const updateSettings = (body) => api.put('/settings', body).then((r) => r.data)

export const getHealth = () => api.get('/health').then((r) => r.data)
