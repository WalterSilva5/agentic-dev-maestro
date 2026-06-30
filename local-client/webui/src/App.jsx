import { NavLink, Route, Routes, Navigate } from 'react-router-dom'
import Projects from './pages/Projects.jsx'
import Board from './pages/Board.jsx'

function Sidebar() {
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
        <NavLink to="/projects">Projetos</NavLink>
      </nav>
    </aside>
  )
}

export default function App() {
  return (
    <div className="layout">
      <Sidebar />
      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/projects" replace />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/board/:projectId" element={<Board />} />
          <Route path="*" element={<div className="muted">Página não encontrada</div>} />
        </Routes>
      </main>
    </div>
  )
}
