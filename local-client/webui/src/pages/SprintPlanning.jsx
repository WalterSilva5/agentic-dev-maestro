import { useEffect, useState } from 'react'
import {
  getBoard,
  getSprints,
  createSprint,
  updateSprint,
  completeSprint,
  deleteSprint,
  updateTask,
  getSprintRetro,
  generateSprintRetro,
  createRetroActions,
} from '../api'
import { t, tf } from '../i18n'

const STATUS_LABELS = { PLANEJADA: 'Planejada', ATIVA: 'Ativa', CONCLUIDA: 'Concluída' }

// Board de alocação: colunas = Backlog + cada sprint. Aqui o objetivo é
// distribuir o backlog nas sprints (não é o fluxo de trabalho).
export default function SprintPlanning({ projectId, onChanged }) {
  const [sprints, setSprints] = useState([])
  const [tasks, setTasks] = useState([]) // todas as tarefas não-arquivadas (achatadas)
  const [error, setError] = useState('')
  const [newSprint, setNewSprint] = useState({ name: '', goal: '', capacity: '', startDate: '', endDate: '' })
  const [retros, setRetros] = useState({}) // { [sprintId]: { retro, loading } }

  const openRetro = async (sp) => {
    setRetros((r) => ({ ...r, [sp.id]: { ...(r[sp.id] || {}), open: true } }))
    if (retros[sp.id]?.retro) return
    try {
      const r = await getSprintRetro(sp.id)
      setRetros((prev) => ({ ...prev, [sp.id]: { open: true, retro: r.retro } }))
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const runRetro = async (sp) => {
    setRetros((r) => ({ ...r, [sp.id]: { ...(r[sp.id] || {}), open: true, loading: true } }))
    try {
      const r = await generateSprintRetro(sp.id)
      setRetros((prev) => ({ ...prev, [sp.id]: { open: true, retro: r.retro, loading: false } }))
    } catch (e) {
      setRetros((prev) => ({ ...prev, [sp.id]: { ...(prev[sp.id] || {}), loading: false } }))
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const retroToTasks = async (sp) => {
    const actions = retros[sp.id]?.retro?.actions || []
    if (!actions.length) return
    try {
      await createRetroActions(sp.id, actions.map((a) => a.title))
      refreshAll()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const load = () => {
    getSprints(projectId)
      .then(setSprints)
      .catch((e) => setError(e.response?.data?.detail || String(e.message || e)))
    getBoard(projectId)
      .then((b) => setTasks(b.columns.flatMap((c) => c.tasks.map((tk) => ({ ...tk, isDone: c.isDone })))))
      .catch((e) => setError(e.response?.data?.detail || String(e.message || e)))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  const refreshAll = () => {
    load()
    onChanged && onChanged()
  }

  const moveTaskToSprint = async (task, value) => {
    try {
      await updateTask(task.code, { sprintId: value === '' ? null : Number(value) })
      refreshAll()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const onCreateSprint = async () => {
    if (!newSprint.name.trim()) return
    try {
      await createSprint(Number(projectId), {
        name: newSprint.name.trim(),
        goal: newSprint.goal.trim() || null,
        capacity: newSprint.capacity ? Number(newSprint.capacity) : null,
        startDate: newSprint.startDate || null,
        endDate: newSprint.endDate || null,
      })
      setNewSprint({ name: '', goal: '', capacity: '', startDate: '', endDate: '' })
      refreshAll()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const act = (fn) => async (sp) => {
    try {
      await fn(sp)
      refreshAll()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }
  const activate = act((sp) => updateSprint(sp.id, { status: 'ATIVA' }))
  const complete = act((sp) => completeSprint(sp.id, {}))
  const remove = act((sp) => deleteSprint(sp.id))

  const tasksOf = (sid) => tasks.filter((tk) => (tk.sprintId ?? null) === sid)
  const committedOf = (sid) => tasksOf(sid).reduce((a, tk) => a + (tk.estimateMd || 0), 0)
  const doneOf = (sid) => tasksOf(sid).filter((tk) => tk.isDone).length

  const moveOptions = (task) => (
    <select
      style={{ fontSize: 11, width: '100%' }}
      value={task.sprintId ?? ''}
      onChange={(e) => moveTaskToSprint(task, e.target.value)}
      title={t('Mover para')}
    >
      <option value="">{t('Backlog')}</option>
      {sprints.map((sp) => (
        <option key={sp.id} value={sp.id}>
          {sp.name}
        </option>
      ))}
    </select>
  )

  const TaskCard = ({ task }) => (
    <div className="task">
      <div className="code">{task.code}</div>
      <div className="ttitle">{task.title}</div>
      <span className="badge-type">{task.type}</span>
      <span className={`badge-prio ${task.priority}`}>{task.priority}</span>
      {task.estimateMd ? <span className="muted"> · {task.estimateMd}hd</span> : null}
      <div style={{ marginTop: 6 }}>{moveOptions(task)}</div>
    </div>
  )

  return (
    <div>
      {error && <div className="banner">{error}</div>}

      {/* Criar sprint */}
      <div className="toolbar" style={{ flexWrap: 'wrap', marginBottom: 12 }}>
        <input
          placeholder={t('Nome da sprint')}
          value={newSprint.name}
          onChange={(e) => setNewSprint({ ...newSprint, name: e.target.value })}
        />
        <input
          placeholder={t('Meta/objetivo')}
          value={newSprint.goal}
          onChange={(e) => setNewSprint({ ...newSprint, goal: e.target.value })}
        />
        <input
          type="number"
          min="0"
          style={{ width: 130 }}
          placeholder={t('Capacidade (hd)')}
          value={newSprint.capacity}
          onChange={(e) => setNewSprint({ ...newSprint, capacity: e.target.value })}
        />
        <input
          type="date"
          value={newSprint.startDate}
          onChange={(e) => setNewSprint({ ...newSprint, startDate: e.target.value })}
        />
        <input
          type="date"
          value={newSprint.endDate}
          onChange={(e) => setNewSprint({ ...newSprint, endDate: e.target.value })}
        />
        <button onClick={onCreateSprint}>{t('+ Criar sprint')}</button>
      </div>

      <div className="board">
        {/* Coluna Backlog */}
        <div className="column">
          <h3>
            <span>{t('Backlog')}</span>
            <span className="count">{tasksOf(null).length}</span>
          </h3>
          {tasksOf(null).map((task) => (
            <TaskCard key={task.id} task={task} />
          ))}
          {tasksOf(null).length === 0 && <div className="muted">{t('Vazio')}</div>}
        </div>

        {/* Uma coluna por sprint */}
        {sprints.map((sp) => {
          const committed = committedOf(sp.id)
          const list = tasksOf(sp.id)
          const over = sp.capacity != null && committed > sp.capacity
          const pct = sp.capacity ? Math.min(Math.round((committed / sp.capacity) * 100), 100) : 0
          return (
            <div key={sp.id} className="column">
              <h3 style={{ flexWrap: 'wrap', gap: 4 }}>
                <span>{sp.name}</span>
                <span className="badge-type">{t(STATUS_LABELS[sp.status] || sp.status)}</span>
                <span className="count">{list.length}</span>
              </h3>
              {sp.goal && <div className="muted" style={{ fontSize: 11, marginBottom: 4 }}>{sp.goal}</div>}
              {(sp.startDate || sp.endDate) && (
                <div className="muted" style={{ fontSize: 11 }}>
                  {(sp.startDate || '').slice(0, 10)} → {(sp.endDate || '').slice(0, 10)}
                </div>
              )}
              {/* Capacidade vs comprometido */}
              <div style={{ fontSize: 11, margin: '4px 0', color: over ? 'var(--danger, #e5484d)' : 'inherit' }}>
                {tf('Comprometido {c}hd', { c: committed })}
                {sp.capacity != null ? tf(' / capacidade {cap}hd', { cap: sp.capacity }) : ''}
                {over ? ' ⚠' : ''}{' · '}
                {tf('{d}/{n} concluídas', { d: doneOf(sp.id), n: list.length })}
              </div>
              {sp.capacity != null && (
                <div style={{ background: 'var(--border)', borderRadius: 4, height: 6, overflow: 'hidden', marginBottom: 6 }}>
                  <div style={{ background: over ? 'var(--danger, #e5484d)' : 'var(--accent)', height: '100%', width: `${pct}%` }} />
                </div>
              )}
              {/* Ações da sprint */}
              <div className="row" style={{ gap: 4, flexWrap: 'wrap', marginBottom: 6 }}>
                {sp.status !== 'ATIVA' && sp.status !== 'CONCLUIDA' && (
                  <button className="ghost" style={{ fontSize: 11 }} onClick={() => activate(sp)}>{t('Ativar')}</button>
                )}
                {sp.status !== 'CONCLUIDA' && (
                  <button className="ghost" style={{ fontSize: 11 }} onClick={() => complete(sp)}>{t('Concluir')}</button>
                )}
                <button className="ghost" style={{ fontSize: 11 }} onClick={() => openRetro(sp)}>{t('Retrospectiva')}</button>
                <button
                  className="ghost"
                  style={{ fontSize: 11 }}
                  onClick={() => {
                    if (confirm(t('Excluir a sprint? As tarefas voltam ao backlog.'))) remove(sp)
                  }}
                >
                  {t('Excluir')}
                </button>
              </div>
              {retros[sp.id]?.open && (
                <div className="card" style={{ marginBottom: 6, fontSize: 12 }}>
                  <div className="row" style={{ gap: 6, marginBottom: 4 }}>
                    <button className="ghost" style={{ fontSize: 11 }} disabled={retros[sp.id]?.loading} onClick={() => runRetro(sp)}>
                      {retros[sp.id]?.loading ? t('Gerando...') : (retros[sp.id]?.retro ? t('Regerar com IA') : t('Gerar com IA'))}
                    </button>
                    <button className="ghost" style={{ fontSize: 11 }} onClick={() => setRetros((r) => ({ ...r, [sp.id]: { ...r[sp.id], open: false } }))}>
                      {t('Fechar')}
                    </button>
                  </div>
                  {retros[sp.id]?.retro ? (
                    <div>
                      {retros[sp.id].retro.well?.length > 0 && (
                        <div><b>👍 {t('O que foi bem')}</b><ul style={{ margin: '2px 0 6px' }}>{retros[sp.id].retro.well.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
                      )}
                      {retros[sp.id].retro.badly?.length > 0 && (
                        <div><b>👎 {t('O que pode melhorar')}</b><ul style={{ margin: '2px 0 6px' }}>{retros[sp.id].retro.badly.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
                      )}
                      {retros[sp.id].retro.actions?.length > 0 && (
                        <div>
                          <b>✅ {t('Ações')}</b>
                          <ul style={{ margin: '2px 0 6px' }}>{retros[sp.id].retro.actions.map((a, i) => <li key={i}>{a.title}</li>)}</ul>
                          <button className="ghost" style={{ fontSize: 11 }} onClick={() => retroToTasks(sp)}>{t('Criar tarefas das ações')}</button>
                        </div>
                      )}
                    </div>
                  ) : (
                    !retros[sp.id]?.loading && <div className="muted">{t('Sem retrospectiva ainda. Gere com IA.')}</div>
                  )}
                </div>
              )}
              {list.map((task) => (
                <TaskCard key={task.id} task={task} />
              ))}
              {list.length === 0 && <div className="muted">{t('Vazio')}</div>}
            </div>
          )
        })}
        {sprints.length === 0 && <div className="muted">{t('Crie uma sprint para começar a planejar.')}</div>}
      </div>
    </div>
  )
}
