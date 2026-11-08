import { useEffect, useState } from 'react'
import Swal from 'sweetalert2'
import {
  getEpics,
  getGoals,
  createGoal,
  deleteGoal,
  getProjects,
  getSprints,
} from '../api'
import { t } from '../i18n'

function daysLabel(days) {
  if (days == null) return t('Sem data alvo')
  if (days < 0) return t('Atrasado há {n}d', { n: Math.abs(days) })
  if (days === 0) return t('Vence hoje')
  return t('Faltam {n}d', { n: days })
}

export default function Goals() {
  const [projects, setProjects] = useState([])
  const [projectId, setProjectId] = useState('')
  const [goals, setGoals] = useState([])
  const [epics, setEpics] = useState([])
  const [sprints, setSprints] = useState([])
  const [name, setName] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [tag, setTag] = useState('')
  const [epicId, setEpicId] = useState('')
  const [sprintId, setSprintId] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    getProjects()
      .then((ps) => {
        setProjects(ps)
        if (ps.length > 0) setProjectId((cur) => cur || String(ps[0].id))
      })
      .catch((e) => setError(String(e.message || e)))
  }, [])

  const load = () => {
    if (!projectId) return
    Promise.all([getGoals(projectId), getEpics(projectId), getSprints(projectId)])
      .then(([gs, es, ss]) => {
        setGoals(gs)
        setEpics(es)
        setSprints(ss)
      })
      .catch((e) => setError(String(e.message || e)))
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, [projectId])

  const onCreate = async () => {
    if (!name.trim()) return
    try {
      await createGoal(projectId, {
        name: name.trim(),
        dueDate: dueDate || null,
        tag: tag.trim() || null,
        epicId: epicId ? Number(epicId) : null,
        sprintId: sprintId ? Number(sprintId) : null,
      })
      setName('')
      setDueDate('')
      setTag('')
      setEpicId('')
      setSprintId('')
      setError('')
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const onDelete = async (id) => {
    const res = await Swal.fire({
      title: t('Excluir este goal?'),
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: t('Excluir'),
      cancelButtonText: t('Cancelar'),
    })
    if (!res.isConfirmed) return
    try {
      await deleteGoal(id)
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  return (
    <div>
      <h1 className="page-title">{t('Goals')}</h1>
      <p className="subtitle">{t('Objetivos com progresso e contagem regressiva.')}</p>

      {error && <div className="banner">{error}</div>}

      <div className="toolbar">
        <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.key} · {p.name}
            </option>
          ))}
        </select>
        <input
          placeholder={t('Nome do goal (ex.: entregar onda-1)')}
          value={name}
          style={{ minWidth: 220 }}
          onChange={(e) => setName(e.target.value)}
        />
        <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
        <input
          placeholder={t('Tag (ex.: onda-1)')}
          value={tag}
          style={{ width: 130 }}
          onChange={(e) => setTag(e.target.value)}
        />
        <select value={epicId} onChange={(e) => setEpicId(e.target.value)}>
          <option value="">{t('Épico: qualquer')}</option>
          {epics.map((e) => (
            <option key={e.id} value={e.id}>
              {e.name}
            </option>
          ))}
        </select>
        <select value={sprintId} onChange={(e) => setSprintId(e.target.value)}>
          <option value="">{t('Sprint: qualquer')}</option>
          {sprints.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <button onClick={onCreate}>{t('+ Criar goal')}</button>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: 14,
          marginTop: 12,
        }}
      >
        {goals.map((g) => {
          const p = g.progress || { total: 0, done: 0, pct: 0, daysLeft: null }
          const filters = [
            g.tag ? `#${g.tag}` : null,
            g.epic || null,
            g.sprint || null,
          ].filter(Boolean)
          return (
            <div key={g.id} className="card" style={{ minHeight: 130 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <div style={{ fontWeight: 700, fontSize: 16, flex: 1 }}>{g.name}</div>
                <button
                  className="ghost"
                  title={t('Excluir')}
                  onClick={() => onDelete(g.id)}
                >
                  ✕
                </button>
              </div>
              {filters.length > 0 && (
                <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                  {filters.join(' · ')}
                </div>
              )}
              {g.description && <div style={{ fontSize: 13, marginTop: 4 }}>{g.description}</div>}
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 10 }}>
                <div
                  style={{
                    flex: 1,
                    height: 18,
                    borderRadius: 9,
                    background: 'var(--column, #eef0f3)',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: `${p.pct}%`,
                      height: '100%',
                      background: 'var(--accent, #4f46e5)',
                      color: '#fff',
                      fontSize: 11,
                      fontWeight: 700,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {p.pct}% ({p.done}/{p.total})
                  </div>
                </div>
                <div
                  className="muted"
                  style={{
                    fontSize: 12,
                    fontWeight: 700,
                    color:
                      p.daysLeft != null && p.daysLeft < 0
                        ? 'var(--danger, #e5484d)'
                        : undefined,
                  }}
                >
                  {daysLabel(p.daysLeft)}
                </div>
              </div>
            </div>
          )
        })}
        {goals.length === 0 && <div className="muted">{t('Nenhum goal ainda.')}</div>}
      </div>
    </div>
  )
}
