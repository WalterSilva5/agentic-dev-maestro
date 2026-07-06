import { useEffect, useState } from 'react'
import { NavLink, Route, Routes, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import MeuDia from './pages/MeuDia.jsx'
import Estudos from './pages/Estudos.jsx'
import Projects from './pages/Projects.jsx'
import Board from './pages/Board.jsx'
import Assistente from './pages/Assistente.jsx'
import Metricas from './pages/Metricas.jsx'
import Todos from './pages/Todos.jsx'
import Labels from './pages/Labels.jsx'
import Configuracoes from './pages/Configuracoes.jsx'
import WorkspaceSelector from './components/WorkspaceSelector.jsx'
import PendingTodosReminder from './components/PendingTodosReminder.jsx'
import { getPendingTodos } from './api'
import { getTheme, toggleTheme } from './theme'
import { t } from './i18n'

function Sidebar() {
  const [theme, setTheme] = useState(getTheme())
  const [pendingCount, setPendingCount] = useState(0)

  useEffect(() => {
    const poll = () =>
      getPendingTodos().then((p) => setPendingCount(p?.count || 0)).catch(() => {})
    poll()
    const id = setInterval(poll, 60000)
    return () => clearInterval(id)
  }, [])

  const nav = [
    ['/dashboard', t('Dashboard')],
    ['/meu-dia', t('Meu Dia')],
    ['/estudos', t('Estudos')],
    ['/projetos', t('Projetos')],
    ['/assistente', t('Assistente')],
    ['/metricas', t('Métricas')],
    ['/todos', t('TODOs')],
    ['/labels', t('Labels')],
    ['/configuracoes', t('Configurações')],
  ]
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="badge">A</div>
        <div>
          <div className="name">Agentic Dev</div>
          <div className="sub">Maestro · web</div>
        </div>
      </div>
      <WorkspaceSelector />
      <nav className="nav">
        {nav.map(([to, label]) => (
          <NavLink key={to} to={to}>
            {label}
            {to === '/todos' && pendingCount > 0 && (
              <span
                style={{
                  marginLeft: 6,
                  fontSize: 11,
                  fontWeight: 700,
                  color: 'var(--danger, #e5484d)',
                }}
              >
                ⏰{pendingCount}
              </span>
            )}
          </NavLink>
        ))}
      </nav>
      <button className="theme-toggle" onClick={() => setTheme(toggleTheme())}>
        {theme === 'dark' ? `☀  ${t('Tema claro')}` : `☾  ${t('Tema escuro')}`}
      </button>
    </aside>
  )
}

export default function App() {
  return (
    <div className="layout">
      <Sidebar />
      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/meu-dia" element={<MeuDia />} />
          <Route path="/estudos" element={<Estudos />} />
          <Route path="/projetos" element={<Projects />} />
          <Route path="/board/:projectId" element={<Board />} />
          <Route path="/assistente" element={<Assistente />} />
          <Route path="/metricas" element={<Metricas />} />
          <Route path="/todos" element={<Todos />} />
          <Route path="/labels" element={<Labels />} />
          <Route path="/configuracoes" element={<Configuracoes />} />
          <Route path="*" element={<div className="muted">{t('Página não encontrada')}</div>} />
        </Routes>
      </main>
      <PendingTodosReminder />
    </div>
  )
}
