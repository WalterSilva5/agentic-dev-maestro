import axios from 'axios'

// Em dev o proxy do vite manda /api -> 9777; em prod a FastAPI serve tudo na mesma origem.
export const api = axios.create({ baseURL: '/api' })

// Projetos / board
export const getProjects = () => api.get('/projects').then((r) => r.data)
export const createProject = (body) => api.post('/projects', body).then((r) => r.data)
export const deleteProject = (id) => api.delete(`/projects/${id}`).then((r) => r.data)
export const getBoard = (projectId) => api.get(`/projects/${projectId}/board`).then((r) => r.data)

// Tarefas
export const getTask = (code) => api.get(`/tasks/${code}`).then((r) => r.data)
export const createTask = (body) => api.post('/tasks', body).then((r) => r.data)
export const updateTask = (code, body) => api.patch(`/tasks/${code}`, body).then((r) => r.data)
export const moveTask = (code, columnId) =>
  api.post(`/tasks/${code}/move`, { columnId }).then((r) => r.data)

// Checklist
export const addChecklist = (code, title) =>
  api.post(`/tasks/${code}/checklist`, { title }).then((r) => r.data)
export const toggleChecklist = (id) =>
  api.patch(`/tasks/checklist/${id}/toggle`).then((r) => r.data)
export const deleteChecklist = (id) => api.delete(`/tasks/checklist/${id}`).then((r) => r.data)

// Comentários
export const getComments = (taskId) =>
  api.get('/comments', { params: { taskId } }).then((r) => r.data)
export const addComment = (taskId, body, type = 'COMMENT') =>
  api.post('/comments', { taskId, body, type }).then((r) => r.data)

// Dashboard / métricas / atividade
export const getMetrics = () => api.get('/projects/metrics').then((r) => r.data)
export const getActivity = (limit = 15) =>
  api.get('/activity', { params: { limit } }).then((r) => r.data)
export const getHealth = () => api.get('/health').then((r) => r.data)
