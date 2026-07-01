import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getMetrics, getActivity, getProjects } from '../api'

function fmtWhen(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString(undefined, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null)
  const [activity, setActivity] = useState([])
  const [projects, setProjects] = useState([])
  const [error, setError] = useState('')
  const nav = useNavigate()

  useEffect(() => {
    Promise.all([getMetrics(), getActivity(15), getProjects()])
      .then(([m, a, p]) => {
        setMetrics(m)
        setActivity(a)
        setProjects(p)
      })
      .catch((e) => setError(String(e.message || e)))
  }, [])

  const s = metrics?.summary || {}
  const cards = [
    { lbl: 'Tarefas', val: s.totalTasks ?? '—' },
    { lbl: 'Concluídas', val: s.doneTasks ?? '—' },
    { lbl: 'Lead time (h)', val: s.avgLeadTimeHours != null ? Math.round(s.avgLeadTimeHours) : '—' },
    { lbl: 'Cycle time (h)', val: s.avgCycleTimeHours != null ? Math.round(s.avgCycleTimeHours) : '—' },
  ]

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>
      <p className="subtitle">Visão geral do workspace ativo (via API).</p>
      {error && <div className="banner">{error}</div>}

      <div className="cards-row">
        {cards.map((c) => (
          <div key={c.lbl} className="card summary">
            <div className="val">{c.val}</div>
            <div className="lbl">{c.lbl}</div>
          </div>
        ))}
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h4 style={{ margin: '0 0 8px', color: 'var(--muted)' }}>Atividade recente</h4>
        {activity.length === 0 && <div className="muted">Nenhuma atividade.</div>}
        {activity.map((a) => (
          <div key={a.id} className="activity-item">
            <span className="when">{fmtWhen(a.createdAt)}</span>
            <span><b>{a.action}</b>{a.detail ? ` — ${a.detail}` : ''}</span>
          </div>
        ))}
      </div>

      <div className="card">
        <h4 style={{ margin: '0 0 8px', color: 'var(--muted)' }}>Projetos</h4>
        {projects.map((p) => (
          <div key={p.id} className="activity-item" style={{ cursor: 'pointer' }} onClick={() => nav(`/board/${p.id}`)}>
            <span className="when">{p.key}</span>
            <span>{p.name}</span>
          </div>
        ))}
        {projects.length === 0 && <div className="muted">Nenhum projeto.</div>}
      </div>
    </div>
  )
}
