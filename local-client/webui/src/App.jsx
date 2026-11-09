import { useEffect, useState } from 'react'
import { NavLink, Route, Routes, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import MeuDia from './pages/MeuDia.jsx'
import Estudos from './pages/Estudos.jsx'
import Projects from './pages/Projects.jsx'
import Board from './pages/Board.jsx'
import Assistente from './pages/Assistente.jsx'
import Goals from './pages/Goals.jsx'
import Metricas from './pages/Metricas.jsx'
import Reunioes from './pages/Reunioes.jsx'
import Time from './pages/Time.jsx'
import Todos from './pages/Todos.jsx'
import Labels from './pages/Labels.jsx'
import Biblioteca from './pages/Biblioteca.jsx'
import ApiTester from './pages/ApiTester.jsx'
import Base from './pages/Base.jsx'
import Ferramentas from './pages/Ferramentas.jsx'
import Traducao from './pages/Traducao.jsx'
import Configuracoes from './pages/Configuracoes.jsx'
import WorkspaceSelector from './components/WorkspaceSelector.jsx'
import ProjectSelector from './components/ProjectSelector.jsx'
import PendingTodosReminder from './components/PendingTodosReminder.jsx'
import CoachTip from './components/CoachTip.jsx'
import { getPendingTodos } from './api'
import { t } from './i18n'

function Sidebar({ onNavigate, onCollapse }) {
  const [pendingCount, setPendingCount] = useState(0)

  useEffect(() => {
    const poll = () =>
      getPendingTodos().then((p) => setPendingCount(p?.count || 0)).catch(() => {})
    poll()
    const id = setInterval(poll, 60000)
    return () => clearInterval(id)
  }, [])

  // Menu enxuto: essenciais + hub "Ferramentas" (extras: estudos, métricas,
  // labels, biblioteca, testador de API, base).
  const nav = [
    ['/dashboard', t('Dashboard'), '📊'],
    ['/meu-dia', t('Meu Dia'), '📅'],
    ['/projetos', t('Projetos'), '📁'],
    ['/goals', t('Goals'), '🎯'],
    ['/time', t('Time'), '👥'],
    ['/reunioes', t('Reuniões'), '🎙️'],
    ['/assistente', t('Assistente'), '💬'],
    ['/todos', t('TODOs'), '✅'],
    ['/ferramentas', t('Ferramentas'), '🧰'],
    ['/configuracoes', t('Configurações'), '⚙️'],
    // deep link do app desktop: mesma lista, sem seção própria
    ['relay://vault', t('Senhas'), '🔒', t('Cofre KeePass no desktop')],
  ]
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="badge">A</div>
        <div>
          <div className="name">Agentic Dev</div>
          <div className="sub">Relay · web</div>
        </div>
        <button
          type="button"
          className="icon-btn sidebar-collapse"
          aria-label={t('Ocultar menu')}
          title={t('Ocultar menu (F9)')}
          onClick={onCollapse}
        >
          «
        </button>
      </div>
      <WorkspaceSelector />
      <ProjectSelector />
      <div className="nav-label">{t('Workspace')}</div>
      <nav className="nav">
        {nav.map(([to, label, ico, hint]) =>
          to.startsWith('relay://') ? (
            // atalho do app desktop (abre o Relay nativo)
            <a key={to} href={to} title={hint}>
              <span className="nav-ico">{ico}</span>
              <span>{label}</span>
              <span className="nav-ext">↗</span>
            </a>
          ) : (
            <NavLink key={to} to={to} onClick={onNavigate}>
              <span className="nav-ico">{ico}</span>
              <span>{label}</span>
              {to === '/todos' && pendingCount > 0 && (
                <span
                  style={{
                    marginLeft: 'auto',
                    fontSize: 11,
                    fontWeight: 700,
                    color: 'var(--danger, #e5484d)',
                  }}
                >
                  ⏰{pendingCount}
                </span>
              )}
            </NavLink>
          )
        )}
      </nav>
    </aside>
  )
}

export default function App() {
  const [navOpen, setNavOpen] = useState(false)
  const [sidebarVisible, setSidebarVisible] = useState(() => {
    try { return localStorage.getItem('relay.sidebarVisible') !== 'false' } catch { return true }
  })
  const toggleSidebar = () => {
    setSidebarVisible((v) => {
      const n = !v
      try { localStorage.setItem('relay.sidebarVisible', String(n)) } catch {}
      return n
    })
    setNavOpen(false)
  }
  // Atalho F9 como no desktop
  useEffect(() => {
    const h = (e) => { if (e.key === 'F9') { e.preventDefault(); toggleSidebar() } }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [])
  return (
    <div className={'layout' + (navOpen ? ' nav-open' : '') + (sidebarVisible ? '' : ' sidebar-collapsed')}>
      {/* mobile: abre/fecha a gaveta (no desktop este botão não aparece) */}
      <button
        type="button"
        className="icon-btn floating nav-toggle"
        aria-label={navOpen ? t('Fechar menu') : t('Abrir menu')}
        aria-expanded={navOpen}
        title={navOpen ? t('Fechar menu') : t('Abrir menu')}
        onClick={() => setNavOpen((v) => !v)}
      >
        {navOpen ? '✕' : '☰'}
      </button>
      {navOpen && (
        <button
          type="button"
          className="nav-backdrop"
          aria-label={t('Fechar menu')}
          onClick={() => setNavOpen(false)}
        />
      )}
      {sidebarVisible && <Sidebar onNavigate={() => setNavOpen(false)} onCollapse={toggleSidebar} />}
      {/* desktop recolhido: botão para trazer o menu de volta */}
      {!sidebarVisible && (
        <button
          type="button"
          className="icon-btn floating sidebar-show"
          aria-label={t('Mostrar menu')}
          title={t('Mostrar menu (F9)')}
          onClick={toggleSidebar}
        >
          ☰
        </button>
      )}
      <main className="content" onClick={() => navOpen && setNavOpen(false)}>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/meu-dia" element={<MeuDia />} />
          <Route path="/estudos" element={<Estudos />} />
          <Route path="/projetos" element={<Projects />} />
          <Route path="/projects" element={<Navigate to="/projetos" replace />} />
          <Route path="/board/:projectId" element={<Board />} />
          <Route path="/assistente" element={<Assistente />} />
        <Route path="/goals" element={<Goals />} />
          <Route path="/metricas" element={<Metricas />} />
          <Route path="/time" element={<Time />} />
          <Route path="/reunioes" element={<Reunioes />} />
          <Route path="/todos" element={<Todos />} />
          <Route path="/labels" element={<Labels />} />
          <Route path="/biblioteca" element={<Biblioteca />} />
          <Route path="/api-tester" element={<ApiTester />} />
          <Route path="/base" element={<Base />} />
          <Route path="/ferramentas" element={<Ferramentas />} />
          <Route path="/traducao" element={<Traducao />} />
          <Route path="/configuracoes" element={<Configuracoes />} />
          <Route path="*" element={<div className="muted">{t('Página não encontrada')}</div>} />
        </Routes>
      </main>
      <PendingTodosReminder />
      <CoachTip />
    </div>
  )
}
