import axios from 'axios'

// Em dev o proxy do vite manda /api -> 9777; em prod a FastAPI serve tudo na mesma origem.
export const api = axios.create({ baseURL: '/api' })

export const getProjects = () => api.get('/projects').then((r) => r.data)
export const createProject = (body) => api.post('/projects', body).then((r) => r.data)
export const deleteProject = (id) => api.delete(`/projects/${id}`).then((r) => r.data)
export const getBoard = (projectId) => api.get(`/projects/${projectId}/board`).then((r) => r.data)
export const createTask = (body) => api.post('/tasks', body).then((r) => r.data)
export const moveTask = (code, columnId) =>
  api.post(`/tasks/${code}/move`, { columnId }).then((r) => r.data)
export const getHealth = () => api.get('/health').then((r) => r.data)
