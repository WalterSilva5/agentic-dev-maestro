import { useEffect, useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import Swal from 'sweetalert2'
import {
  getBoard,
  createTask,
  moveTask,
  updateTask,
  getSprints,
  archiveTask,
  unarchiveTask,
  getArchived,
  getGoals,
  getMembers,
  createMember,
  deleteMember,
  updateProject,
  getLinks,
  createLink,
  updateLink,
  deleteLink,
} from '../api'
import TaskDetail from '../components/TaskDetail.jsx'
import SprintPlanning from './SprintPlanning.jsx'
import { t, tf } from '../i18n'

const SPRINT_STATUS_LABELS = {
  PLANEJADA: 'Planejada',
  ATIVA: 'Ativa',
  CONCLUIDA: 'Concluída',
}

function PieChart({ data, size = 110 }) {
  const total = data.reduce((a, b) => a + (b.value || 0), 0)
  if (!total) return <div className="muted" style={{ fontSize: 11 }}>{'Sem dados'}</div>
  let acc = 0
  const r = size / 2
  const cx = r, cy = r
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ flexShrink: 0 }}>
      {data.map((d, i) => {
        const angle = (d.value / total) * 360
        const start = acc
        acc += angle
        const sr = (start - 90) * Math.PI / 180
        const er = (start + angle - 90) * Math.PI / 180
        const x1 = cx + r * Math.cos(sr), y1 = cy + r * Math.sin(sr)
        const x2 = cx + r * Math.cos(er), y2 = cy + r * Math.sin(er)
        const large = angle > 180 ? 1 : 0
        return <path key={i} d={`M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`} fill={d.color} stroke="var(--card)" strokeWidth="1.5" />
      })}
      <circle cx={cx} cy={cy} r={r * 0.52} fill="var(--card)" />
      <text x={cx} y={cy} textAnchor="middle" dominantBaseline="middle" fontSize="11" fontWeight="700" fill="var(--text)">{total}</text>
    </svg>
  )
}
const PIE_COLORS = ['#4f46e5','#06b6d4','#f59e0b','#ef4444','#10b981','#8b5cf6','#ec4899','#6366f1','#14b8a6','#f97316']

export default function Board() {
  const { projectId } = useParams()
  const [board, setBoard] = useState(null)
  const [error, setError] = useState('')
  const [newTitles, setNewTitles] = useState({})
  const [openCode, setOpenCode] = useState(null)

  // Abas: board de fluxo | planejamento de sprints
  const [view, setView] = useState('board') // 'board' | 'planning'

  // Sprints
  const [sprints, setSprints] = useState([])
  const [sprintFilter, setSprintFilter] = useState('all') // 'all' | 'backlog' | <id>
  const defaultedRef = useRef(false) // já aplicou o default (sprint ativa) para este projeto?

  // Arquivados
  const [archived, setArchived] = useState([])
  const [showArchived, setShowArchived] = useState(false)

  // Métricas do projeto (acordeão)
  const [goals, setGoals] = useState([])
  const [metricsOpen, setMetricsOpen] = useState(true)
  const [members, setMembers] = useState([])
  const [showMembers, setShowMembers] = useState(false)
  const [newMemberName, setNewMemberName] = useState('')
  const [links, setLinks] = useState([])
  const [newLinkTitle, setNewLinkTitle] = useState('')
  const [newLinkUrl, setNewLinkUrl] = useState('')
  const [editingLink, setEditingLink] = useState(null)

  // Filtros (paridade com desktop FilterBar)
  const [searchText, setSearchText] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('all')
  const [epicFilter, setEpicFilter] = useState('all')
  const [tagFilter, setTagFilter] = useState('all')
  const [assigneeFilter, setAssigneeFilter] = useState('all')

  const filterParam = sprintFilter === 'all' ? null : sprintFilter

  const load = () =>
    getBoard(projectId, filterParam)
      .then(setBoard)
      .catch((e) => setError(String(e.message || e)))

  const loadSprints = () =>
    getSprints(projectId)
      .then((sp) => {
        setSprints(sp)
        // Ao abrir o projeto, o board mostra a sprint ativa por padrão.
        if (!defaultedRef.current) {
          defaultedRef.current = true
          const active = sp.find((s) => s.status === 'ATIVA')
          if (active) setSprintFilter(String(active.id))
        }
      })
      .catch((e) => setError(e.response?.data?.detail || String(e.message || e)))

  const loadArchived = () =>
    getArchived(projectId)
      .then(setArchived)
      .catch((e) => setError(e.response?.data?.detail || String(e.message || e)))

  const loadGoals = () =>
    getGoals(projectId)
      .then(setGoals)
      .catch(() => setGoals([]))

  const loadMembers = () =>
    getMembers(projectId)
      .then(setMembers)
      .catch(() => setMembers([]))

  const loadLinks = () =>
    getLinks(projectId)
      .then(setLinks)
      .catch(() => setLinks([]))

  useEffect(() => {
    // Novo projeto: re-aplica o default (sprint ativa) e volta pra aba Board.
    defaultedRef.current = false
    setSprintFilter('all')
    setView('board')
  }, [projectId])

  useEffect(() => {
    load()
    loadSprints()
    loadArchived()
    loadGoals()
    loadMembers()
    loadLinks()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, sprintFilter])

  const addTask = async (columnId) => {
    const title = (newTitles[columnId] || '').trim()
    if (!title) return
    const body = { projectId: Number(projectId), columnId, title, type: 'FEATURE', priority: 'MEDIUM' }
    // Cria já dentro da sprint selecionada (se for uma sprint específica)
    if (sprintFilter !== 'all' && sprintFilter !== 'backlog') body.sprintId = Number(sprintFilter)
    try {
      await createTask(body)
      setNewTitles({ ...newTitles, [columnId]: '' })
      load()
      loadSprints()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const advance = async (task, columns) => {
    const idx = columns.findIndex((c) => c.id === task.columnId)
    const next = columns[idx + 1]
    if (!next) return
    try {
      await moveTask(task.code, next.id)
      load()
      loadSprints()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const onArchive = async (task) => {
    try {
      await archiveTask(task.code)
      load()
      loadArchived()
      loadSprints()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const onUnarchive = async (task) => {
    try {
      await unarchiveTask(task.code)
      load()
      loadArchived()
      loadSprints()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const assignSprint = async (task, value) => {
    try {
      await updateTask(task.code, { sprintId: value === '' ? null : Number(value) })
      load()
      loadSprints()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const assignTask = async (task, assignee) => {
    const val = (assignee || '').trim() || null
    try {
      if (val) { try { await createMember(projectId, { name: val }) } catch {} }
      await updateTask(task.code, { assignee: val })
      load()
      loadMembers()
    } catch (e) { setError(e.response?.data?.detail || String(e.message || e)) }
  }

  const handleCreateMember = async () => {
    const name = newMemberName.trim()
    if (!name) return
    try { await createMember(projectId, { name }); setNewMemberName(''); loadMembers() } catch (e) { setError(e.response?.data?.detail || String(e.message || e)) }
  }

  const handleDeleteMember = async (id) => {
    try { await deleteMember(id); loadMembers(); load() } catch (e) { setError(String(e.message || e)) }
  }

  const handleCreateLink = async () => {
    const title = newLinkTitle.trim()
    const url = newLinkUrl.trim()
    if (!title || !url) return
    try { await createLink(projectId, { title, url }); setNewLinkTitle(''); setNewLinkUrl(''); loadLinks() } catch (e) { setError(e.response?.data?.detail || String(e.message || e)) }
  }
  const handleUpdateLink = async () => {
    if (!editingLink) return
    const title = (editingLink.title || '').trim()
    const url = (editingLink.url || '').trim()
    if (!title || !url) return
    try { await updateLink(editingLink.id, { title, url }); setEditingLink(null); loadLinks() } catch (e) { setError(e.response?.data?.detail || String(e.message || e)) }
  }
  const handleDeleteLink = async (id) => {
    try { await deleteLink(id); loadLinks() } catch (e) { setError(String(e.message || e)) }
  }

  if (error) return <div className="banner">{error}</div>
  if (!board) return <div className="muted">{t('Carregando...')}</div>

  const cols = [...board.columns].sort((a, b) => a.order - b.order)
  const activeSprint = sprints.find((s) => s.status === 'ATIVA')

  // — Métricas do projeto (mesmo cálculo do desktop) —
  const doneColIds = new Set(cols.filter((c) => c.isDone).map((c) => c.id))
  const tasksAll = cols.flatMap((c) => c.tasks)
  const totalTasks = tasksAll.length
  const doneTasks = tasksAll.filter((tk) => doneColIds.has(tk.columnId)).length
  const pct = totalTasks ? Math.round((doneTasks / totalTasks) * 100) : 0
  const wipAlerts = cols.filter((c) => c.wipLimit && c.wipLimit > 0 && c.tasks.length > c.wipLimit)
  const today0 = new Date(); today0.setHours(0,0,0,0)
  const vencidos = tasksAll.filter((tk) => tk.dueDate && new Date(tk.dueDate) < today0 && !doneColIds.has(tk.columnId))
  const limiteParado = Date.now() - 14 * 24 * 60 * 60 * 1000
  const parados = tasksAll.filter((tk) => !doneColIds.has(tk.columnId) && tk.updatedAt && new Date(tk.updatedAt).getTime() < limiteParado)
  const goalsAtrasados = goals.filter((g) => {
    if (!g.dueDate) return false
    if (new Date(g.dueDate) >= today0) return false
    let q = tasksAll
    if (g.tag) q = q.filter((tk) => tk.labels?.some((l) => l.name === g.tag))
    if (g.epicId) q = q.filter((tk) => tk.epics?.some((e) => e.id === g.epicId))
    if (g.sprintId) q = q.filter((tk) => tk.sprintId === g.sprintId)
    const tot = q.length
    const done = q.filter((tk) => doneColIds.has(tk.columnId)).length
    return done < tot
  }).length
  const metricSummary = []
  if (pct < 100) metricSummary.push(`${pct}%`)
  if (wipAlerts.length) metricSummary.push(`⚠ WIP ${wipAlerts.length}`)
  if (vencidos.length) metricSummary.push(`⏰ ${vencidos.length} vencida(s)`)
  if (parados.length) metricSummary.push(`• ${parados.length} parada(s)`)
  if (goalsAtrasados) metricSummary.push(`🎯 ${goalsAtrasados} atrasado(s)`)
  const goalProgress = (g) => {
    let q = tasksAll
    if (g.tag) q = q.filter((tk) => tk.labels?.some((l) => l.name === g.tag))
    if (g.epicId) q = q.filter((tk) => tk.epics?.some((e) => e.id === g.epicId))
    if (g.sprintId) q = q.filter((tk) => tk.sprintId === g.sprintId)
    const tot = q.length; const done = q.filter((tk) => doneColIds.has(tk.columnId)).length
    return [done, tot, tot ? Math.round(done/tot*100) : 0]
  }
  const daysUntil = (d) => Math.round((new Date(d) - today0) / 86400000)
  const colorForDays = (d, warn=7) => d < 0 ? 'var(--danger)' : d <= warn ? '#d97706' : 'var(--text)'

  // Filtros derivados (client-side)
  const epicOptions = [...new Set(tasksAll.flatMap((tk) => (tk.epics || []).map((e) => e.name)))].sort()
  const tagOptions = [...new Set(tasksAll.flatMap((tk) => (tk.labels || []).map((l) => l.name)))].sort()
  const assigneeOptions = [...new Set([...tasksAll.map((tk) => tk.assignee).filter(Boolean), ...members.map((m) => m.name)])].sort()
  const filteredCols = cols.map((col) => ({
    ...col,
    tasks: col.tasks.filter((tk) => {
      const s = searchText.trim().toLowerCase()
      if (s && !((tk.title || '').toLowerCase().includes(s) || (tk.code || '').toLowerCase().includes(s))) return false
      if (priorityFilter !== 'all' && tk.priority !== priorityFilter) return false
      if (epicFilter !== 'all' && !(tk.epics || []).some((e) => e.name === epicFilter)) return false
      if (tagFilter !== 'all' && !(tk.labels || []).some((l) => l.name === tagFilter)) return false
      if (assigneeFilter !== 'all') {
        if (assigneeFilter === '__none__') { if (tk.assignee) return false }
        else if (tk.assignee !== assigneeFilter) return false
      }
      return true
    }),
  }))
  const visibleCount = filteredCols.reduce((a, c) => a + c.tasks.length, 0)
  const PRIORITY_COLORS = { LOW: '#71717A', MEDIUM: '#4f46e5', HIGH: '#EA580C', URGENT: '#DC2626' }
  const epicProgressList = [...new Map(tasksAll.flatMap((tk) => tk.epics || []).map((ep) => [ep.id, ep])).values()].map((ep) => {
    const q = tasksAll.filter((tk) => tk.epics.some((e) => e.id === ep.id))
    const tot = q.length; const done = q.filter((tk) => doneColIds.has(tk.columnId)).length
    return { ep, done, tot, pct: tot ? Math.round((done / tot) * 100) : 0 }
  }).sort((a, b) => b.tot - a.tot).slice(0, 8)
  const unassignedTasks = tasksAll.filter((tk) => !tk.assignee)
  const unassignedTot = unassignedTasks.length
  const unassignedDone = unassignedTasks.filter((tk) => doneColIds.has(tk.columnId)).length
  const unassignedPct = unassignedTot ? Math.round((unassignedDone / unassignedTot) * 100) : 0
  const assigneeProgressListBase = assigneeOptions.map((name) => {
    const q = tasksAll.filter((tk) => tk.assignee === name)
    const tot = q.length; const done = q.filter((tk) => doneColIds.has(tk.columnId)).length
    return { name, done, tot, pct: tot ? Math.round((done / tot) * 100) : 0 }
  })
  if (unassignedTot > 0) assigneeProgressListBase.push({ name: 'Sem responsável', done: unassignedDone, tot: unassignedTot, pct: unassignedPct, isUnassigned: true })
  const assigneeProgressList = assigneeProgressListBase.sort((a, b) => b.tot - a.tot).slice(0, 8)
  const activeFilterCount = (searchText.trim() ? 1 : 0) + (priorityFilter !== 'all' ? 1 : 0) + (epicFilter !== 'all' ? 1 : 0) + (tagFilter !== 'all' ? 1 : 0) + (assigneeFilter !== 'all' ? 1 : 0)
  // Pie data
  const columnPieData = cols.map((c, i) => ({ label: c.name, value: c.tasks.length, color: PIE_COLORS[i % PIE_COLORS.length] })).filter((d) => d.value > 0)
  const assigneePieData = assigneeProgressList.map((a, i) => ({ label: a.name, value: a.tot, color: a.isUnassigned ? '#9ca3af' : PIE_COLORS[i % PIE_COLORS.length] }))
  const priorityPieData = ['URGENT','HIGH','MEDIUM','LOW'].map((p) => ({ label: p, value: tasksAll.filter((t) => t.priority === p).length, color: PRIORITY_COLORS[p] })).filter((d) => d.value > 0)
  const epicPieData = epicProgressList.map((e, i) => ({ label: e.ep.name, value: e.tot, color: e.ep.color || PIE_COLORS[i % PIE_COLORS.length] }))

  return (
    <div>
      <div className="row" style={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
        <h1 className="page-title" style={{ margin: 0 }}>
          {board.key} · {board.name}
        </h1>
        <div className="row" style={{ gap: 8 }}>
          {board.boardUrl ? (
            <>
              <a href={board.boardUrl} target="_blank" rel="noreferrer"><button className="ghost" style={{ background: '#0078d4', color: '#fff', borderColor: '#0078d4' }}>🔗 {t('Abrir board')}</button></a>
              <button className="ghost" title={board.boardUrl} onClick={async ()=>{
                const { value: v } = await Swal.fire({ title: t('Link do board externo (cole a URL):'), input: 'url', inputValue: board.boardUrl || '', inputPlaceholder: 'https://...', showCancelButton: true, confirmButtonText: t('Salvar'), cancelButtonText: t('Cancelar') })
                if(v!==undefined) updateProject(projectId, { boardUrl: (v||'').trim() }).then(load)
              }}>{t('Editar link')}</button>
            </>
          ) : (
            <button className="ghost" onClick={async ()=>{
              const { value: v } = await Swal.fire({ title: t('Link do board externo (cole a URL):'), input: 'url', inputPlaceholder: 'https://...', showCancelButton: true, confirmButtonText: t('Salvar'), cancelButtonText: t('Cancelar') })
              if(v!==undefined) updateProject(projectId, { boardUrl: (v||'').trim() }).then(load)
            }}>{t('Definir link do Board')}</button>
          )}
          <Link to="/projetos"><button className="ghost">{t('← Projetos')}</button></Link>
        </div>
      </div>
      <p className="subtitle">{tf('Board kanban via API ({count} colunas).', { count: cols.length })}</p>

      {/* Abas: board de fluxo | planejamento de sprints | métricas */}
      <div className="row" style={{ gap: 6, marginBottom: 10 }}>
        <button className={view === 'board' ? '' : 'ghost'} onClick={() => setView('board')}>
          {t('Board')}
        </button>
        <button className={view === 'metrics' ? '' : 'ghost'} onClick={() => setView('metrics')}>
          {t('Métricas')}
        </button>
        <button className={view === 'planning' ? '' : 'ghost'} onClick={() => setView('planning')}>
          {t('Planejamento de Sprints')}
        </button>
      </div>

      {view === 'planning' ? (
        <SprintPlanning
          projectId={projectId}
          onChanged={() => {
            load()
            loadSprints()
          }}
        />
      ) : view === 'metrics' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Métricas — conteúdo completo sem acordeão */}
          <div className="card" style={{ padding: '14px', display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <strong>{t('Métricas do projeto')}</strong>
              <span className="muted" style={{ fontSize: 11 }}>{metricSummary.length ? metricSummary.join('  ·  ') : t('Tudo em dia')}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="muted" style={{ fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap' }}>{t('Progresso geral')}</span>
              <div style={{ flex: 1, height: 14, background: 'var(--border-light)', borderRadius: 6, overflow: 'hidden', display: 'flex' }}>
                <div style={{ width: `${pct}%`, background: pct === 100 ? 'var(--accent)' : 'var(--accent)', transition: 'width .3s' }} />
              </div>
              <span style={{ fontSize: 12, fontWeight: 600, minWidth: 80, textAlign: 'right' }}>{pct}% ({doneTasks}/{totalTasks})</span>
              {activeSprint?.endDate && (() => {
                const d = daysUntil(activeSprint.endDate)
                const col = d < 0 ? 'var(--danger)' : d <= 3 ? '#d97706' : 'var(--muted)'
                return (
                  <span style={{ fontSize: 11, color: col }}>
                    {d >= 0 ? tf('Sprint {name}: {d} dias', { name: activeSprint.name, d }) : tf('Sprint {name}: atrasada {d}d', { name: activeSprint.name, d: Math.abs(d) })}
                  </span>
                )
              })()}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border-light)', borderRadius: 8, padding: '8px 10px' }}>
                <div className="muted" style={{ fontSize: 10, fontWeight: 700, letterSpacing: .6, textTransform: 'uppercase', marginBottom: 4 }}>{t('Alertas')}</div>
                {wipAlerts.length===0 && vencidos.length===0 && parados.length===0
                  ? <div className="muted" style={{ fontSize: 12 }}>{t('Nenhum alerta — fluxo saudável.')}</div>
                  : <>
                    {wipAlerts.slice(0,3).map((a,i)=>(<div key={i} style={{ color: 'var(--danger)', fontSize: 12 }}>{'\u2022'} WIP: {a}</div>))}
                    {vencidos.slice(0,3).map((tk)=>(<div key={tk.id} style={{ color: 'var(--danger)', fontSize: 12 }}>{'\u2022'} {tk.code} vencida</div>))}
                    {parados.slice(0,3).map((tk)=>(<div key={tk.id} style={{ color: '#d97706', fontSize: 12 }}>{'\u2022'} {tk.code} parada</div>))}
                  </>}
              </div>
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border-light)', borderRadius: 8, padding: '8px 10px' }}>
                <div className="muted" style={{ fontSize: 10, fontWeight: 700, letterSpacing: .6, textTransform: 'uppercase', marginBottom: 4 }}>{t('Prazos')}</div>
                {goals.filter((g)=>g.dueDate).length===0 && !activeSprint?.endDate
                  ? <div className="muted" style={{ fontSize: 12 }}>{t('Nenhum prazo definido.')}</div>
                  : <>
                    {activeSprint?.endDate && (<div style={{ fontSize: 12, color: colorForDays(daysUntil(activeSprint.endDate), 7) }}>{'\u2022'} Sprint {activeSprint.name}: {new Date(activeSprint.endDate).toLocaleDateString()}</div>)}
                    {goals.filter((g)=>g.dueDate).slice(0,4).map((g)=>{ const [d,tot]=goalProgress(g); const days=daysUntil(g.dueDate); const col=colorForDays(days, 7); return (<div key={g.id} style={{ fontSize: 12, color: col }}>{'\u2022'} {g.name} — {new Date(g.dueDate).toLocaleDateString()} ({days}d) {d}/{tot}</div>) })}
                  </>}
              </div>
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border-light)', borderRadius: 8, padding: '8px 10px' }}>
                <div className="muted" style={{ fontSize: 10, fontWeight: 700, letterSpacing: .6, textTransform: 'uppercase', marginBottom: 4 }}>{t('Objetivos')}</div>
                {goals.length===0
                  ? <div className="muted" style={{ fontSize: 12 }}>{t('Nenhum goal — crie em Goals.')}</div>
                  : goals.slice(0,4).map((g)=>{ const [d,tot,p]=goalProgress(g); const days=g.dueDate?Math.round((new Date(g.dueDate)-today0)/86400000):null; return (
                    <div key={g.id} style={{ marginBottom: 6 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 6, fontSize: 12, fontWeight: 600 }}><span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{g.name}</span>{days!==null && <span style={{ color: days<0?'var(--danger)':days<=3?'#d97706':'var(--muted)', fontSize: 11 }}>{days>=0?`${days}d`:`${Math.abs(days)}d atraso`}</span>}</div>
                      <div style={{ height: 8, background: 'var(--border-light)', borderRadius: 4, overflow: 'hidden', marginTop: 2 }}><div style={{ width: `${p}%`, height: '100%', background: 'var(--accent)' }} /></div>
                      <div className="muted" style={{ fontSize: 10 }}>{p}% ({d}/{tot})</div>
                    </div>
                  )})}
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 10 }}>
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border-light)', borderRadius: 8, padding: '8px 10px' }}>
                <div className="muted" style={{ fontSize: 10, fontWeight: 700, letterSpacing: .6, textTransform: 'uppercase', marginBottom: 6 }}>{t('Por módulo (épico)')}</div>
                {epicPieData.length > 0 && (
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 8 }}>
                    <PieChart data={epicPieData} size={90} />
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
                      {epicPieData.slice(0,4).map((d,i)=>(<div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}><span style={{ width: 10, height: 10, borderRadius: 2, background: d.color }} />{d.label} <span className="muted">({d.value})</span></div>))}
                      {epicPieData.length>4 && <div className="muted" style={{ fontSize: 10 }}>+{epicPieData.length-4} {t('outros')}</div>}
                    </div>
                  </div>
                )}
                {epicProgressList.length === 0
                  ? <div className="muted" style={{ fontSize: 12 }}>{t('Nenhum épico vinculado.')}</div>
                  : epicProgressList.map(({ ep, done, tot, pct: p }) => (
                    <div key={ep.id} style={{ marginBottom: 6 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 6, fontSize: 12, fontWeight: 600 }}>
                        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: ep.color || 'var(--text)', borderLeft: `3px solid ${ep.color || '#7c85ff'}`, paddingLeft: 6 }}>{ep.name}</span>
                        <span className="muted" style={{ fontSize: 11 }}>{p}% ({done}/{tot})</span>
                      </div>
                      <div style={{ height: 6, background: 'var(--border-light)', borderRadius: 4, overflow: 'hidden', marginTop: 2 }}><div style={{ width: `${p}%`, height: '100%', background: ep.color || 'var(--accent)' }} /></div>
                    </div>
                  ))}
              </div>
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border-light)', borderRadius: 8, padding: '8px 10px' }}>
                <div className="muted" style={{ fontSize: 10, fontWeight: 700, letterSpacing: .6, textTransform: 'uppercase', marginBottom: 6 }}>{t('Por responsável')}</div>
                {assigneePieData.length > 0 && (
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 8 }}>
                    <PieChart data={assigneePieData} size={90} />
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
                      {assigneePieData.slice(0,4).map((d,i)=>(<div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}><span style={{ width: 10, height: 10, borderRadius: 2, background: d.color }} />{d.label} <span className="muted">({d.value})</span></div>))}
                      {assigneePieData.length>4 && <div className="muted" style={{ fontSize: 10 }}>+{assigneePieData.length-4} {t('outros')}</div>}
                    </div>
                  </div>
                )}
                {assigneeProgressList.length === 0
                  ? <div className="muted" style={{ fontSize: 12 }}>{t('Nenhum responsável atribuído.')}</div>
                  : assigneeProgressList.map(({ name, done, tot, pct: p, isUnassigned }) => (
                    <div key={name} style={{ marginBottom: 6 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 6, fontSize: 12, fontWeight: 600 }}>
                        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: isUnassigned ? '#9ca3af' : 'var(--text)' }}>{name} {isUnassigned && `(${unassignedTot})`}</span>
                        <span className="muted" style={{ fontSize: 11 }}>{p}% ({done}/{tot})</span>
                      </div>
                      <div style={{ height: 6, background: 'var(--border-light)', borderRadius: 4, overflow: 'hidden', marginTop: 2 }}><div style={{ width: `${p}%`, height: '100%', background: isUnassigned ? '#9ca3af' : 'var(--accent)' }} /></div>
                    </div>
                  ))}
              </div>
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border-light)', borderRadius: 8, padding: '8px 10px' }}>
                <div className="muted" style={{ fontSize: 10, fontWeight: 700, letterSpacing: .6, textTransform: 'uppercase', marginBottom: 6 }}>{t('Distribuição por coluna')}</div>
                {columnPieData.length > 0 && (
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 8 }}>
                    <PieChart data={columnPieData} size={90} />
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
                      {columnPieData.slice(0,4).map((d,i)=>(<div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}><span style={{ width: 10, height: 10, borderRadius: 2, background: d.color }} />{d.label} <span className="muted">({d.value})</span></div>))}
                    </div>
                  </div>
                )}
                {cols.map((c) => {
                  const pctCol = c.tasks.length ? Math.round((c.tasks.filter((tk) => doneColIds.has(tk.columnId)).length / c.tasks.length) * 100) : 0
                  const over = c.wipLimit && c.tasks.length > c.wipLimit
                  return (
                    <div key={c.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12, padding: '2px 0', color: over ? 'var(--danger)' : 'var(--text)' }}>
                      <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.name}</span>
                      <span style={{ fontWeight: 700, marginLeft: 8 }}>{c.tasks.length}{c.wipLimit ? `/${c.wipLimit}` : ''}</span>
                      <span className="muted" style={{ fontSize: 10, marginLeft: 6 }}>{c.isDone ? '✓' : `${pctCol}%`}</span>
                    </div>
                  )
                })}
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 }}>
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border-light)', borderRadius: 8, padding: '8px 10px' }}>
                <div className="muted" style={{ fontSize: 10, fontWeight: 700, letterSpacing: .6, textTransform: 'uppercase', marginBottom: 6 }}>{t('Por prioridade')}</div>
                {priorityPieData.length > 0 ? (
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <PieChart data={priorityPieData} size={90} />
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4 }}>
                      {priorityPieData.map((d,i)=>(<div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}><span style={{ width: 10, height: 10, borderRadius: 2, background: d.color }} />{d.label} <span className="muted">({d.value})</span></div>))}
                    </div>
                  </div>
                ) : <div className="muted" style={{ fontSize: 12 }}>{t('Sem dados')}</div>}
              </div>
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border-light)', borderRadius: 8, padding: '8px 10px' }}>
                <div className="muted" style={{ fontSize: 10, fontWeight: 700, letterSpacing: .6, textTransform: 'uppercase', marginBottom: 6 }}>{t('Métricas de fluxo')}</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="muted">{t('WIP total')}</span><span style={{ fontWeight: 700 }}>{tasksAll.filter((tk)=>!doneColIds.has(tk.columnId)).length} {t('em aberto')}</span></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="muted">{t('Vencidas')}</span><span style={{ fontWeight: 700, color: vencidos.length?'var(--danger)':'var(--text)' }}>{vencidos.length}</span></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="muted">{t('Paradas 14d+')}</span><span style={{ fontWeight: 700, color: parados.length?'#d97706':'var(--text)' }}>{parados.length}</span></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="muted">{t('Sem responsável')}</span><span style={{ fontWeight: 700 }}>{unassignedTot} ({unassignedPct}%)</span></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="muted">{t('Concluídas')}</span><span style={{ fontWeight: 700, color: 'var(--accent)' }}>{doneTasks}/{totalTasks} ({pct}%)</span></div>
                </div>
              </div>
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border-light)', borderRadius: 8, padding: '8px 10px' }}>
                <div className="muted" style={{ fontSize: 10, fontWeight: 700, letterSpacing: .6, textTransform: 'uppercase', marginBottom: 6 }}>{t('Filtros')}</div>
                <div className="muted" style={{ fontSize: 11 }}>{activeFilterCount === 0 ? t('Nenhum filtro ativo — mostrando tudo') : tf('{visible}/{total} visíveis com filtros', { visible: visibleCount, total: totalTasks })}</div>
                <div style={{ marginTop: 6, height: 6, background: 'var(--border-light)', borderRadius: 4, overflow: 'hidden' }}><div style={{ width: `${totalTasks?Math.round(visibleCount/totalTasks*100):0}%`, height: '100%', background: 'var(--accent)' }} /></div>
                <div className="muted" style={{ fontSize: 10, marginTop: 4 }}>{t('Use Buscar, Prioridade, Épico, Tag, Responsável acima')}</div>
              </div>
            </div>
            {/* Hierárquico por módulos — barra proporcional */}
            <div style={{ background: 'var(--bg)', border: '1px solid var(--border-light)', borderRadius: 8, padding: '10px', marginTop: 4 }}>
              <div className="muted" style={{ fontSize: 10, fontWeight: 700, letterSpacing: .6, textTransform: 'uppercase', marginBottom: 6 }}>📊 {t('Progresso por módulos e submódulos')}</div>
              <div style={{ height: 14, background: 'var(--border-light)', borderRadius: 7, overflow: 'hidden', display: 'flex' }}><div style={{ width: `${pct}%`, background: pct===100?'#16a34a':'#f59e0b' }} /></div>
              <div className="muted" style={{ fontSize: 10, marginTop: 4 }}>{doneTasks}/{totalTasks} · {pct}%</div>
            </div>
            {/* Hierárquico detalhado por módulos/submódulos (como SVG) */}
            <div style={{ background: 'var(--bg)', border: '1px solid var(--border-light)', borderRadius: 8, padding: '10px', marginTop: 8 }}>
              <div className="muted" style={{ fontSize: 10, fontWeight: 700, letterSpacing: .6, textTransform: 'uppercase', marginBottom: 6 }}>📊 {t('Detalhamento por módulo')}</div>
              {(() => {
                const moduleTags = ['auth','cashier','config','financeiro','troca','venda','voucher','tef','acordo','monitor','estatisticas','batch','abend','crm','tudoav','cobransaas','cliente']
                const modSet = new Set(moduleTags.map((m)=>m.toLowerCase()))
                const byModule = {}
                for (const tk of tasksAll) {
                  const mods = (tk.labels||[]).map((l)=>l.name.toLowerCase()).filter((n)=>modSet.has(n))
                  for (const m of mods) { if (!byModule[m]) byModule[m]=[]; byModule[m].push(tk) }
                }
                const moduleKeys = Object.keys(byModule).sort((a,b)=>byModule[b].length - byModule[a].length)
                if (moduleKeys.length===0) return <div className="muted" style={{ fontSize: 11 }}>{t('Nenhum módulo com tarefas etiquetadas.')}</div>
                const maxBar = Math.max(...moduleKeys.map((k)=>byModule[k].length),1)
                const groups = { concluido: [], andamento: [], naoIniciado: [] }
                for (const mod of moduleKeys) {
                  const tot=byModule[mod].length; const done=byModule[mod].filter((tk)=>doneColIds.has(tk.columnId)).length; const p=tot?done/tot:0
                  if (p===1) groups.concluido.push(mod); else if (p===0) groups.naoIniciado.push(mod); else groups.andamento.push(mod)
                }
                return (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {['concluido','andamento','naoIniciado'].map((grp)=>{
                      const mods=groups[grp]; if(mods.length===0) return null
                      const titles={concluido:'CONCLUÍDOS',andamento:'EM ANDAMENTO',naoIniciado:'NÃO INICIADOS'}
                      return (
                        <div key={grp}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                            <span style={{ width: 4, height: 16, borderRadius: 2, background: grp==='concluido'?'#16a34a':grp==='andamento'?'#f59e0b':'#cbd5e1' }} />
                            <span style={{ fontWeight: 800, fontSize: 10, letterSpacing: .5 }}>{t(titles[grp])}</span>
                            <span className="muted" style={{ fontSize: 11 }}>{mods.length} {t('módulo(s)')} · {mods.reduce((a,m)=>a+byModule[m].length,0)} {t('tarefas')}</span>
                          </div>
                          {mods.map((mod)=>{
                            const tasksMod=byModule[mod]; const tot=tasksMod.length; const done=tasksMod.filter((tk)=>doneColIds.has(tk.columnId)).length; const p=tot?Math.round(done/tot*100):0; const barW=Math.max(14, Math.round((tot/maxBar)*460))
                            const subTags={}; for(const tk of tasksMod){ for(const lb of tk.labels||[]){ const n=lb.name; if(n.includes('-') && n.toLowerCase()!==mod && !['sprint-1','sprint-2','sprint-3','sprint-4','sprint-5','vm','var-mobile','var3-app','fundacao','infra','despriorizado'].includes(n.toLowerCase())){ const pre=mod.slice(0,3).toLowerCase(); if(n.toLowerCase().startsWith(pre) || (n.toLowerCase().startsWith('onda-')&&mod==='cashier')||(n.toLowerCase().startsWith('tro-')&&mod==='troca')||(n.toLowerCase().startsWith('ven-')&&mod==='venda')||(n.toLowerCase().startsWith('fin-')&&mod==='financeiro')){ if(!subTags[n]) subTags[n]=[]; subTags[n].push(tk) } } } }
                            const subKeys=Object.keys(subTags).sort()
                            return (
                              <div key={mod} style={{ marginBottom: 8, border: '1px solid var(--border-light)', borderRadius: 8, padding: '8px 10px', background: 'var(--card)' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                                  <span style={{ fontWeight: 700, fontSize: 12, textTransform: 'capitalize' }}>{mod} <span className="muted" style={{ fontWeight: 400, fontSize: 11 }}>· {tot} {t('tarefas')}</span></span>
                                  <span style={{ fontSize: 11, fontWeight: 700 }}>{done}/{tot} — {p}%</span>
                                </div>
                                <div style={{ height: 10, background: 'var(--border-light)', borderRadius: 5, overflow: 'hidden', marginTop: 4, maxWidth: barW }}><div style={{ width: `${p}%`, height: '100%', background: p===100?'#16a34a':p>0?'#f59e0b':'var(--border-light)' }} /></div>
                                {subKeys.length>0 && (
                                  <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 3, paddingLeft: 10, borderLeft: '2px solid var(--border-light)' }}>
                                    {subKeys.map((sub)=>{
                                      const q=subTags[sub]; const totS=q.length; const doneS=q.filter((tk)=>doneColIds.has(tk.columnId)).length; const pS=totS?Math.round(doneS/totS*100):0; const barSW=Math.max(10, Math.round((totS/maxBar)*460*0.6))
                                      return (
                                        <div key={sub} style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10 }}><span className="muted">{sub}</span><span style={{ fontWeight: 600 }}>{doneS}/{totS} — {pS}%</span></div>
                                          <div style={{ height: 6, background: 'var(--border-light)', borderRadius: 3, overflow: 'hidden', maxWidth: barSW }}><div style={{ width: `${pS}%`, height: '100%', background: pS===100?'#16a34a':pS>0?'#f59e0b':'var(--border-light)' }} /></div>
                                        </div>
                                      )
                                    })}
                                  </div>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      )
                    })}
                  </div>
                )
              })()}
            </div>
          </div>
        )}
      </div>
      ) : (
        <>
      {/* Barra de sprints */}
      <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 10 }}>
        <span className="muted">{t('Sprint:')}</span>
        <select value={sprintFilter} onChange={(e) => setSprintFilter(e.target.value)}>
          <option value="all">{t('Todas')}</option>
          <option value="backlog">{t('Backlog')}</option>
          {sprints.map((sp) => (
            <option key={sp.id} value={sp.id}>
              {sp.name} · {t(SPRINT_STATUS_LABELS[sp.status] || sp.status)} ({sp.doneCount}/{sp.taskCount})
            </option>
          ))}
        </select>
        {activeSprint && sprintFilter === 'all' && (
          <button className="ghost" onClick={() => setSprintFilter(String(activeSprint.id))}>
            {tf('Ver sprint ativa: {name}', { name: activeSprint.name })}
          </button>
        )}
        <button className="ghost" onClick={() => setShowArchived((v) => !v)}>
          {showArchived ? t('← Voltar ao board') : tf('Arquivados ({count})', { count: archived.length })}
        </button>
        <button className="ghost" onClick={() => setShowMembers(true)}>{t('Responsáveis')} ({members.length})</button>
      </div>

      {/* Atalhos do projeto — links com título (PRs, docs, board externo, etc) */}
      <div className="card" style={{ padding: '10px 14px', marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <strong>🔗 {t('Atalhos')}</strong>
          <span className="muted" style={{ fontSize: 11 }}>{links.length} {t('atalho(s)')}</span>
        </div>
        {links.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
            {links.map((l) => (
              <span key={l.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 20, padding: '4px 10px', fontSize: 12 }}>
                <a href={l.url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)', textDecoration: 'none', fontWeight: 600 }}>{l.title} ↗</a>
                <button className="ghost" style={{ padding: '1px 6px', fontSize: 10 }} onClick={() => setEditingLink(l)}>{t('Editar')}</button>
                <button className="ghost" style={{ padding: '1px 6px', fontSize: 10, color: 'var(--danger)' }} onClick={() => handleDeleteLink(l.id)}>✕</button>
              </span>
            ))}
          </div>
        )}
        {editingLink ? (
          <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
            <input placeholder={t('Título do atalho')} value={editingLink.title} onChange={(e)=>setEditingLink({...editingLink, title: e.target.value})} style={{ flex: '1 1 140px' }} />
            <input placeholder="https://..." value={editingLink.url} onChange={(e)=>setEditingLink({...editingLink, url: e.target.value})} style={{ flex: '2 1 260px' }} />
            <button onClick={handleUpdateLink}>{t('Salvar')}</button>
            <button className="ghost" onClick={()=>setEditingLink(null)}>{t('Cancelar')}</button>
          </div>
        ) : (
          <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
            <input placeholder={t('Título do atalho')} value={newLinkTitle} onChange={(e)=>setNewLinkTitle(e.target.value)} style={{ flex: '1 1 140px' }} />
            <input placeholder="https://..." value={newLinkUrl} onChange={(e)=>setNewLinkUrl(e.target.value)} style={{ flex: '2 1 260px' }} onKeyDown={(e)=>e.key==='Enter' && handleCreateLink()} />
            <button onClick={handleCreateLink}>{t('+ Adicionar atalho')}</button>
          </div>
        )}
        <div className="muted" style={{ fontSize: 11, marginTop: 6 }}>{t('Ex.: PR da sprint, doc de migração, board externo, pipeline.')}</div>
      </div>

      {/* Barra de filtros (paridade desktop FilterBar) */}
      {!showArchived && view === 'board' && (
        <div className="card" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 10, padding: '10px 12px' }}>
          <input placeholder={t('🔍 Buscar por título ou código...')} value={searchText} onChange={(e) => setSearchText(e.target.value)} style={{ minWidth: 180, flex: '1 1 180px' }} />
          <span className="muted" style={{ fontSize: 11, fontWeight: 700 }}>{t('Prioridade:')}</span>
          <select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)} style={{ minWidth: 110 }}><option value="all">{t('Todas')}</option><option value="LOW">{t('Baixa')}</option><option value="MEDIUM">{t('Média')}</option><option value="HIGH">{t('Alta')}</option><option value="URGENT">{t('Urgente')}</option></select>
          <span className="muted" style={{ fontSize: 11, fontWeight: 700 }}>{t('Épico:')}</span>
          <select value={epicFilter} onChange={(e) => setEpicFilter(e.target.value)} style={{ minWidth: 110 }}><option value="all">{t('Todos')}</option>{epicOptions.map((ep) => (<option key={ep} value={ep}>{ep}</option>))}</select>
          <span className="muted" style={{ fontSize: 11, fontWeight: 700 }}>{t('Tag:')}</span>
          <select value={tagFilter} onChange={(e) => setTagFilter(e.target.value)} style={{ minWidth: 110 }}><option value="all">{t('Todas')}</option>{tagOptions.map((tg) => (<option key={tg} value={tg}>{tg}</option>))}</select>
          <span className="muted" style={{ fontSize: 11, fontWeight: 700 }}>{t('Responsável:')}</span>
          <select value={assigneeFilter} onChange={(e) => setAssigneeFilter(e.target.value)} style={{ minWidth: 120 }}><option value="all">{t('Todos')}</option><option value="__none__">{t('Sem responsável')}</option>{assigneeOptions.map((a) => (<option key={a} value={a}>{a}</option>))}</select>
          <span className="muted" style={{ fontSize: 11, marginLeft: 'auto' }}>{visibleCount === totalTasks ? tf('{total} tarefas', { total: totalTasks }) : tf('{visible}/{total} tarefas', { visible: visibleCount, total: totalTasks })}</span>
          <button className="ghost" onClick={() => { setSearchText(''); setPriorityFilter('all'); setEpicFilter('all'); setTagFilter('all'); setAssigneeFilter('all') }}>{t('Limpar')}</button>
        </div>
      )}

      {showArchived && (
        <div className="card">
          <strong>{t('Tarefas arquivadas')}</strong>
          <div className="muted" style={{ margin: '4px 0 8px' }}>
            {t('Cards concluídos há mais de 3 dias são arquivados automaticamente e somem do board.')}
          </div>
          {archived.length === 0 && <div className="muted">{t('Nenhuma tarefa arquivada.')}</div>}
          {archived.map((task) => (
            <div key={task.id} className="row" style={{ alignItems: 'center' }}>
              <div onClick={() => setOpenCode(task.code)} style={{ cursor: 'pointer' }}>
                <span className="code">{task.code}</span> {task.title}{' '}
                <span className="badge-type">{task.type}</span>{' '}
                <span className={`badge-prio ${task.priority}`}>{task.priority}</span>
              </div>
              <button className="ghost" onClick={() => onUnarchive(task)}>
                {t('Desarquivar')}
              </button>
            </div>
          ))}
        </div>
      )}

      {!showArchived && (
      <div className="board">
        {filteredCols.map((col) => {
          const orig = cols.find((c) => c.id === col.id)
          const wipOver = orig?.wipLimit && orig.tasks.length > orig.wipLimit
          const countText = orig?.wipLimit ? `${col.tasks.length}/${orig.wipLimit}` : String(col.tasks.length)
          return (
          <div key={col.id} className="column">
            <h3>
              <span>{col.name}</span>
              <span className="count" style={wipOver ? { color: 'var(--danger)', fontWeight: 700 } : {}} title={wipOver ? t('Acima do WIP') : ''}>{countText}</span>
            </h3>
            {col.tasks.length === 0 && <div className="muted" style={{ fontSize: 11, textAlign: 'center', padding: 8 }}>{t('Vazio')}</div>}
            {col.tasks.map((task) => (
              <div key={task.id} className="task" onClick={() => setOpenCode(task.code)} style={{ borderLeft: `4px solid ${PRIORITY_COLORS[task.priority] || '#71717A'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6 }}>
                  <span className="code" style={{ fontFamily: 'monospace', fontSize: 10 }}>{task.code}</span>
                  {task.assignee && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--muted)' }}>{task.assignee}</span>
                      <span style={{ width: 18, height: 18, borderRadius: 9, background: 'var(--accent)', color: '#fff', fontSize: 9, fontWeight: 700, display: 'grid', placeItems: 'center' }} title={task.assignee}>{(task.assignee || '').split(' ').slice(0,2).map((p)=>p[0]?.toUpperCase()).join('') || '?'}</span>
                    </span>
                  )}
                </div>
                <div className="ttitle" style={{ fontSize: 13, margin: '4px 0 6px' }}>{task.title}</div>
                {(task.epics?.length > 0 || task.labels?.length > 0) && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 4 }}>
                    {(task.epics || []).slice(0,2).map((ep) => (<span key={ep.id} style={{ border: `1px solid ${ep.color || '#7c85ff'}`, color: ep.color || '#7c85ff', borderRadius: 10, padding: '1px 6px', fontSize: 10, fontWeight: 600 }}>{ep.name}</span>))}
                    {(task.labels || []).slice(0,4).map((lb) => (<span key={lb.id} style={{ background: lb.color || '#6b7280', color: '#fff', borderRadius: 10, padding: '1px 6px', fontSize: 10 }}>{lb.name}</span>))}
                  </div>
                )}
                {task.dueDate && (
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 11, color: task.dueDate && new Date(task.dueDate) < today0 && !doneColIds.has(task.columnId) ? 'var(--danger)' : 'var(--muted)' }}>
                    <span style={{ fontWeight: task.dueDate && new Date(task.dueDate) < today0 && !doneColIds.has(task.columnId) ? 700 : 400 }}>📅 {new Date(task.dueDate).toLocaleDateString()}</span>
                  </div>
                )}
                <div className="row" style={{ marginTop: 6 }} onClick={(e) => e.stopPropagation()}>
                  <select
                    style={{ fontSize: 11, flex: 1 }}
                    value={task.sprintId ?? ''}
                    onChange={(e) => assignSprint(task, e.target.value)}
                    title={t('Sprint da tarefa')}
                  >
                    <option value="">{t('Backlog')}</option>
                    {sprints.map((sp) => (
                      <option key={sp.id} value={sp.id}>
                        {sp.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="row" style={{ marginTop: 6 }} onClick={(e) => e.stopPropagation()}>
                  <select
                    style={{ fontSize: 11, flex: 1 }}
                    value={task.assignee || ''}
                    onChange={(e) => assignTask(task, e.target.value)}
                    title={t('Responsável')}
                  >
                    <option value="">{t('Sem responsável')}</option>
                    {assigneeOptions.map((a) => (<option key={a} value={a}>{a}</option>))}
                    {task.assignee && !assigneeOptions.includes(task.assignee) && (<option value={task.assignee}>{task.assignee}</option>)}
                  </select>
                </div>
                {!col.isDone && (
                  <div>
                    <button
                      className="ghost move"
                      onClick={(e) => {
                        e.stopPropagation()
                        advance(task, cols)
                      }}
                    >
                      {t('Mover →')}
                    </button>
                  </div>
                )}
                {col.isDone && (
                  <div>
                    <button
                      className="ghost move"
                      onClick={(e) => {
                        e.stopPropagation()
                        onArchive(task)
                      }}
                    >
                      {t('Arquivar')}
                    </button>
                  </div>
                )}
              </div>
            ))}
            <div className="row" style={{ marginTop: 6 }}>
              <input
                placeholder={t('Nova tarefa...')}
                style={{ flex: 1, fontSize: 12 }}
                value={newTitles[col.id] || ''}
                onChange={(e) => setNewTitles({ ...newTitles, [col.id]: e.target.value })}
                onKeyDown={(e) => e.key === 'Enter' && addTask(col.id)}
              />
            </div>
          </div>
          )
        })}
      </div>
      )}
        </>
      )}

      {showMembers && (
        <div className="overlay" onClick={()=>setShowMembers(false)}>
          <div className="modal" onClick={(e)=>e.stopPropagation()}>
            <button className="close-x" onClick={()=>setShowMembers(false)}>✕</button>
            <h2>{t('Responsáveis do projeto')}</h2>
            <p className="muted">{t('Quem aparece aqui pode ser atribuído aos cards e filtrado no board.')}</p>
            <div className="row" style={{ marginTop: 12 }}>
              <input placeholder={t('Nome do responsável...')} value={newMemberName} onChange={(e)=>setNewMemberName(e.target.value)} style={{ flex: 1 }} onKeyDown={(e)=>e.key==='Enter' && handleCreateMember()} />
              <button onClick={handleCreateMember}>{t('Adicionar')}</button>
            </div>
            <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {members.length===0 && <div className="muted">{t('Nenhum responsável ainda. Adicione acima.')}</div>}
              {members.map((m)=>{
                const stats = (() => {
                  const q = tasksAll.filter((tk)=>tk.assignee===m.name)
                  const tot=q.length
                  const done=q.filter((tk)=>doneColIds.has(tk.columnId)).length
                  const pct=tot?Math.round(done/tot*100):0
                  const overdue=q.filter((tk)=>tk.dueDate && new Date(tk.dueDate)<today0 && !doneColIds.has(tk.columnId)).length
                  return {tot, done, pct, overdue}
                })()
                return (
                  <div key={m.id} className="card" style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ width: 16, height: 16, borderRadius: 8, background: m.color || 'var(--accent)' }} />
                      <strong style={{ flex: 1 }}>{m.name}</strong>
                      <button className="ghost" style={{ color: 'var(--danger)', padding: '2px 8px' }} onClick={()=>handleDeleteMember(m.id)}>{t('Excluir')}</button>
                    </div>
                    <div style={{ height: 8, background: 'var(--border-light)', borderRadius: 4, overflow: 'hidden' }}><div style={{ width: `${stats.pct}%`, height: '100%', background: 'var(--accent)' }} /></div>
                    <div className="muted" style={{ fontSize: 11 }}>{stats.tot} {t('tarefas')} · {stats.done} {t('concluídas')} {stats.overdue?`· ${stats.overdue} ${t('vencida(s)')}`:''} · {stats.pct}%</div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {openCode && (
        <TaskDetail
          code={openCode}
          onClose={() => setOpenCode(null)}
          onChanged={() => {
            load()
            loadSprints()
          }}
        />
      )}
    </div>
  )
}
