import { useState } from 'react'
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
import { getTheme, toggleTheme } from './theme'

const NAV = [
  ['/dashboard', 'Dashboard'],
  ['/meu-dia', 'Meu Dia'],
  ['/estudos', 'Estudos'],
  ['/projetos', 'Projetos'],
  ['/assistente', 'Assistente'],
  ['/metricas', 'Métricas'],
  ['/todos', 'TODOs'],
  ['/labels', 'Labels'],
  ['/configuracoes', 'Configurações'],
]

function Sidebar() {
  const [theme, setTheme] = useState(getTheme())
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
        {NAV.map(([to, label]) => (
          <NavLink key={to} to={to}>{label}</NavLink>
        ))}
      </nav>
      <button className="theme-toggle" onClick={() => setTheme(toggleTheme())}>
        {theme === 'dark' ? '☀  Tema claro' : '☾  Tema escuro'}
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
          <Route path="*" element={<div className="muted">Página não encontrada</div>} />
        </Routes>
      </main>
    </div>
  )
}
