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
import Swal from 'sweetalert2'
import { getPendingTodos, createBackup, backupDownloadUrl } from './api'
import { getTheme, toggleTheme } from './theme'
import { t } from './i18n'

function Sidebar({ onNavigate, onCollapse }) {
  const [theme, setTheme] = useState(getTheme())
  const [pendingCount, setPendingCount] = useState(0)
  const [backupando, setBackupando] = useState(false)

  const fazerBackup = async () => {
    setBackupando(true)
    try {
      const d = await createBackup()
      const b = (d.backups || [])[0]
      const mb = b ? (b.bytes / 1024 / 1024).toFixed(2) : '0'
      const r = await Swal.fire({
        icon: 'success',
        title: t('Backup concluído'),
        html: `<div style="font-size:12px;text-align:left;line-height:1.6">
          <div><b>${t('Arquivo')}:</b> ${b?.file || '-'}</div>
          <div><b>${t('Pasta')}:</b> ${d.dir}</div>
          <div><b>${t('Tamanho')}:</b> ${mb} MB</div>
        </div>`,
        showDenyButton: true,
        confirmButtonText: t('Fechar'),
        denyButtonText: t('Baixar'),
      })
      if (r.isDenied && b) window.open(backupDownloadUrl(b.file), '_blank')
    } catch (e) {
      const detalhe = e?.response?.data?.detail
      Swal.fire({
        icon: 'error',
        title: t('Falha no backup'),
        text: typeof detalhe === 'string' ? detalhe : (e?.message || ''),
      })
    } finally {
      setBackupando(false)
    }
  }

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
    ['/reunioes', t('Reuniões'), '🎙️'],
    ['/assistente', t('Assistente'), '💬'],
    ['/todos', t('TODOs'), '✅'],
    ['/ferramentas', t('Ferramentas'), '🧰'],
    ['/configuracoes', t('Configurações'), '⚙️'],
  ]
  // Abre o app desktop (nativo) na tela pedida. Funciona se o atalho
  // maestro:// estiver registrado; senão o navegador só ignora o clique
  // e o usuário pode abrir o Maestro desktop manualmente.
  const desktopLinks = [
    ['maestro://vault', '🔒', t('Senhas (app)'), t('Cofre KeePass no desktop')],
  ]
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="badge">A</div>
        <div>
          <div className="name">Agentic Dev</div>
          <div className="sub">Maestro · web</div>
        </div>
        <button
          className="sidebar-collapse"
          aria-label={t('Ocultar menu')}
          title={t('Ocultar menu')}
          onClick={onCollapse}
          style={{ marginLeft: 'auto', background: 'transparent', border: '1px solid var(--border)', color: 'var(--muted)', padding: '4px 8px', fontSize: 12 }}
        >
          ◀
        </button>
      </div>
      <WorkspaceSelector />
      <ProjectSelector />
      <div className="nav-label">{t('Workspace')}</div>
      <nav className="nav">
        {nav.map(([to, label, ico]) => (
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
        ))}
      </nav>
      <div className="nav-label">{t('No app desktop')}</div>
      <nav className="nav">
        {desktopLinks.map(([href, ico, label, hint]) => (
          <a key={href} href={href} title={hint} className="nav-desktop-link">
            <span className="nav-ico">{ico}</span>
            <span>{label}</span>
            <span className="nav-ext">↗</span>
          </a>
        ))}
      </nav>
      <button
        className="theme-toggle"
        onClick={fazerBackup}
        disabled={backupando}
        title={t('Copia o banco do workspace ativo para a pasta de backup do servidor')}
      >
        {backupando ? `⏳ ${t('Fazendo backup...')}` : `💾 ${t('Backup rápido')}`}
      </button>
      <button className="theme-toggle" onClick={() => setTheme(toggleTheme())}>
        {theme === 'dark' ? `☀  ${t('Tema claro')}` : `☾  ${t('Tema escuro')}`}
      </button>
    </aside>
  )
}

export default function App() {
  const [navOpen, setNavOpen] = useState(false)
  const [sidebarVisible, setSidebarVisible] = useState(() => {
    try { return localStorage.getItem('maestro.sidebarVisible') !== 'false' } catch { return true }
  })
  const toggleSidebar = () => {
    setSidebarVisible((v) => {
      const n = !v
      try { localStorage.setItem('maestro.sidebarVisible', String(n)) } catch {}
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
      <button
        className="nav-toggle"
        aria-label={t('Menu')}
        onClick={() => (sidebarVisible ? toggleSidebar() : setNavOpen((v) => !v))}
        title={sidebarVisible ? t('Ocultar menu (F9)') : t('Mostrar menu (F9)')}
      >
        {navOpen ? '✕' : '☰'}
      </button>
      {sidebarVisible && <Sidebar onNavigate={() => setNavOpen(false)} onCollapse={toggleSidebar} />}
      {!sidebarVisible && (
        <button
          className="sidebar-show"
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
