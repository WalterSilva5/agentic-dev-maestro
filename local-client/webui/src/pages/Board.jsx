import { useEffect, useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
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
} from '../api'
import TaskDetail from '../components/TaskDetail.jsx'
import SprintPlanning from './SprintPlanning.jsx'
import { t, tf } from '../i18n'

const SPRINT_STATUS_LABELS = {
  PLANEJADA: 'Planejada',
  ATIVA: 'Ativa',
  CONCLUIDA: 'Concluída',
}

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

  return (
    <div>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h1 className="page-title">
          {board.key} · {board.name}
        </h1>
        <Link to="/projects"><button className="ghost">{t('← Projetos')}</button></Link>
      </div>
      <p className="subtitle">{tf('Board kanban via API ({count} colunas).', { count: cols.length })}</p>

      {/* Abas: board de fluxo | planejamento de sprints */}
      <div className="row" style={{ gap: 6, marginBottom: 10 }}>
        <button className={view === 'board' ? '' : 'ghost'} onClick={() => setView('board')}>
          {t('Board')}
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
      </div>

      {/* Métricas do projeto — acordeão (web) */}
      <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: 12 }}>
        <div
          role="button"
          onClick={() => setMetricsOpen((v) => !v)}
          style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', cursor: 'pointer', userSelect: 'none' }}
        >
          <button className="ghost" style={{ padding: '2px 8px', minWidth: 0 }} onClick={(e) => { e.stopPropagation(); setMetricsOpen((v) => !v) }}>
            {metricsOpen ? '▾' : '▸'}
          </button>
          <strong>{t('Métricas do projeto')}</strong>
          <span className="muted" style={{ fontSize: 11 }}>{metricSummary.length ? metricSummary.join('  ·  ') : t('Tudo em dia')}</span>
        </div>
        {metricsOpen && (
          <div style={{ padding: '0 14px 14px', display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Progresso geral */}
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
            {/* 3 colunas: Alertas | Prazos | Objetivos */}
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
          </div>
        )}
      </div>

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
        {cols.map((col) => (
          <div key={col.id} className="column">
            <h3>
              <span>{col.name}</span>
              <span className="count">{col.tasks.length}</span>
            </h3>
            {col.tasks.map((task) => (
              <div key={task.id} className="task" onClick={() => setOpenCode(task.code)}>
                <div className="code">{task.code}</div>
                <div className="ttitle">{task.title}</div>
                <span className="badge-type">{task.type}</span>
                <span className={`badge-prio ${task.priority}`}>{task.priority}</span>
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
        ))}
      </div>
      )}
        </>
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
