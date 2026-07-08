import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getMetrics, getActivity, getProjects, getDigest } from '../api'
import { t } from '../i18n'

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
  const [digest, setDigest] = useState(null)
  const [digestLoading, setDigestLoading] = useState(false)
  const nav = useNavigate()

  const runDigest = () => {
    setDigestLoading(true)
    getDigest(1)
      .then(setDigest)
      .catch((e) => setError(e.response?.data?.detail || String(e.message || e)))
      .finally(() => setDigestLoading(false))
  }

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
    { lbl: t('Tarefas'), val: s.totalTasks ?? '—' },
    { lbl: t('Concluídas'), val: s.doneTasks ?? '—' },
    { lbl: t('Lead time (h)'), val: s.avgLeadTimeHours != null ? Math.round(s.avgLeadTimeHours) : '—' },
    { lbl: t('Cycle time (h)'), val: s.avgCycleTimeHours != null ? Math.round(s.avgCycleTimeHours) : '—' },
  ]

  return (
    <div>
      <h1 className="page-title">{t('Dashboard')}</h1>
      <p className="subtitle">{t('Visão geral do workspace ativo (via API).')}</p>
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
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <h4 style={{ margin: 0, color: 'var(--muted)' }}>{t('Digest (standup)')}</h4>
          <button className="ghost" onClick={runDigest} disabled={digestLoading}>
            {digestLoading ? t('Gerando...') : t('Gerar com IA')}
          </button>
        </div>
        {digest ? (
          <div style={{ marginTop: 8, fontSize: 13 }}>
            {digest.summary && <p style={{ marginTop: 0 }}>{digest.summary}</p>}
            {digest.done?.length > 0 && (
              <div><b>✅ {t('Feito')}</b><ul style={{ margin: '2px 0 6px' }}>{digest.done.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
            )}
            {digest.doing?.length > 0 && (
              <div><b>🔨 {t('Fazendo')}</b><ul style={{ margin: '2px 0 6px' }}>{digest.doing.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
            )}
            {digest.blockers?.length > 0 && (
              <div><b>🚧 {t('Bloqueios')}</b><ul style={{ margin: '2px 0 6px' }}>{digest.blockers.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
            )}
          </div>
        ) : (
          <div className="muted" style={{ marginTop: 6 }}>{t('Gere um resumo "feito/fazendo/bloqueios" do seu trabalho recente.')}</div>
        )}
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h4 style={{ margin: '0 0 8px', color: 'var(--muted)' }}>{t('Atividade recente')}</h4>
        {activity.length === 0 && <div className="muted">{t('Nenhuma atividade.')}</div>}
        {activity.map((a) => (
          <div key={a.id} className="activity-item">
            <span className="when">{fmtWhen(a.createdAt)}</span>
            <span><b>{a.action}</b>{a.detail ? ` — ${a.detail}` : ''}</span>
          </div>
        ))}
      </div>

      <div className="card">
        <h4 style={{ margin: '0 0 8px', color: 'var(--muted)' }}>{t('Projetos')}</h4>
        {projects.map((p) => (
          <div key={p.id} className="activity-item" style={{ cursor: 'pointer' }} onClick={() => nav(`/board/${p.id}`)}>
            <span className="when">{p.key}</span>
            <span>{p.name}</span>
          </div>
        ))}
        {projects.length === 0 && <div className="muted">{t("Nenhum projeto.")}</div>}
      </div>
    </div>
  )
}
