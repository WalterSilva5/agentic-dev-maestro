import { useEffect, useState } from 'react'
import { getDaily, saveDaily, genDailyReport, getDailyActivity } from '../api'

function fmtWhen(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

export default function MeuDia() {
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [body, setBody] = useState('')
  const [report, setReport] = useState('')
  const [activity, setActivity] = useState([])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [generating, setGenerating] = useState(false)

  function load(d) {
    setError('')
    Promise.all([getDaily(d), getDailyActivity(d)])
      .then(([daily, acts]) => {
        setBody(daily?.body || '')
        setReport(daily?.report || '')
        setActivity(Array.isArray(acts) ? acts : [])
      })
      .catch((e) => setError(String(e.message || e)))
  }

  useEffect(() => {
    load(date)
  }, [date])

  function onSave() {
    setError('')
    setSaving(true)
    saveDaily(date, body)
      .catch((e) => setError(String(e.message || e)))
      .finally(() => setSaving(false))
  }

  function onGenerate() {
    setError('')
    setGenerating(true)
    genDailyReport(date)
      .then((r) => {
        setReport(r?.report || '')
        load(date)
      })
      .catch((e) => setError(String(e.message || e)))
      .finally(() => setGenerating(false))
  }

  return (
    <div>
      <h1 className="page-title">Meu Dia</h1>
      <p className="subtitle">Anote o que você fez hoje e gere um relatório do dia.</p>
      {error && <div className="banner">{error}</div>}

      <div className="toolbar" style={{ marginBottom: 16 }}>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="row" style={{ justifyContent: 'space-between', marginBottom: 8 }}>
          <h4 style={{ margin: 0, color: 'var(--muted)' }}>Nota do dia</h4>
        </div>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Escreva sua nota em markdown..."
          rows={14}
          style={{ width: '100%', boxSizing: 'border-box', resize: 'vertical' }}
        />
        <div className="toolbar" style={{ marginTop: 8 }}>
          <button onClick={onSave} disabled={saving}>
            {saving ? 'Salvando...' : 'Salvar'}
          </button>
          <button className="ghost" onClick={onGenerate} disabled={generating}>
            {generating ? 'Gerando...' : 'Gerar relatório do dia'}
          </button>
        </div>
      </div>

      {report && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h4 style={{ margin: '0 0 8px', color: 'var(--muted)' }}>Relatório do dia</h4>
          <div style={{ whiteSpace: 'pre-wrap' }}>{report}</div>
        </div>
      )}

      <div className="card">
        <h4 style={{ margin: '0 0 8px', color: 'var(--muted)' }}>Atividade do dia</h4>
        {activity.length === 0 && <div className="muted">Nenhuma atividade.</div>}
        {activity.map((a, i) => (
          <div key={a.id ?? i} className="activity-item">
            <span className="when">{fmtWhen(a.createdAt)}</span>
            <span>
              <b>{a.action}</b>
              {a.detail ? ` — ${a.detail}` : ''}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
