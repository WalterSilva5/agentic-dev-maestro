import { useState } from 'react'
import { NavLink, Route, Routes, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import Projects from './pages/Projects.jsx'
import Board from './pages/Board.jsx'
import { getTheme, toggleTheme } from './theme'

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
      <nav className="nav">
        <NavLink to="/dashboard">Dashboard</NavLink>
        <NavLink to="/projects">Projetos</NavLink>
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
          <Route path="/projects" element={<Projects />} />
          <Route path="/board/:projectId" element={<Board />} />
          <Route path="*" element={<div className="muted">Página não encontrada</div>} />
        </Routes>
      </main>
    </div>
  )
}
