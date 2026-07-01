import { useEffect, useState } from 'react'
import { getMetrics } from '../api'
import { t } from '../i18n'

export default function Metricas() {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    getMetrics()
      .then((m) => setMetrics(m))
      .catch((e) => setError(String(e.message || e)))
      .finally(() => setLoading(false))
  }, [])

  const s = metrics?.summary || {}
  const cards = [
    { lbl: t('Total'), val: s.totalTasks ?? '—' },
    { lbl: t('Concluídas'), val: s.doneTasks ?? '—' },
    { lbl: t('Concluídas 7d'), val: s.completedLast7d ?? '—' },
    { lbl: t('Concluídas 30d'), val: s.completedLast30d ?? '—' },
    { lbl: t('Lead time médio (h)'), val: s.avgLeadTimeHours != null ? Math.round(s.avgLeadTimeHours) : '—' },
    { lbl: t('Cycle time médio (h)'), val: s.avgCycleTimeHours != null ? Math.round(s.avgCycleTimeHours) : '—' },
  ]

  const weekly = metrics?.weeklyThroughput || []
  const maxWeekly = weekly.reduce((mx, w) => Math.max(mx, w.count || 0), 0) || 1

  const byType = metrics?.byType || {}
  const byPriority = metrics?.byPriority || {}
  const perProject = metrics?.perProject || []

  function distSection(title, dict) {
    const entries = Object.entries(dict)
    const total = entries.reduce((acc, [, v]) => acc + (v || 0), 0) || 1
    return (
      <div className="card" style={{ marginBottom: 16 }}>
        <h4 style={{ margin: '0 0 12px', color: 'var(--muted)' }}>{title}</h4>
        {entries.length === 0 && <div className="muted">{t("Sem dados.")}</div>}
        {entries.map(([label, count]) => {
          const pct = Math.round(((count || 0) / total) * 100)
          return (
            <div key={label} className="row" style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span style={{ width: 120, flexShrink: 0 }}>{label}</span>
              <span className="muted" style={{ width: 40, flexShrink: 0, textAlign: 'right' }}>{count}</span>
              <div style={{ flex: 1, background: 'var(--border)', borderRadius: 4, height: 12, overflow: 'hidden' }}>
                <div style={{ width: `${pct}%`, height: '100%', background: 'var(--accent)' }} />
              </div>
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div>
      <h1 className="page-title">{t("Métricas")}</h1>
      <p className="subtitle">{t("Indicadores de fluxo e produtividade do workspace ativo (via API).")}</p>
      {error && <div className="banner">{error}</div>}
      {loading && !error && <div className="muted">{t("Carregando…")}</div>}

      {metrics && (
        <>
          <div className="cards-row">
            {cards.map((c) => (
              <div key={c.lbl} className="card summary">
                <div className="val">{c.val}</div>
                <div className="lbl">{c.lbl}</div>
              </div>
            ))}
          </div>

          <div className="card" style={{ marginBottom: 16 }}>
            <h4 style={{ margin: '0 0 12px', color: 'var(--muted)' }}>{t("Throughput semanal")}</h4>
            {weekly.length === 0 && <div className="muted">{t("Sem dados.")}</div>}
            {weekly.length > 0 && (
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 140 }}>
                {weekly.map((w) => (
                  <div key={w.week} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1 }}>
                    <div className="muted" style={{ fontSize: 11, marginBottom: 4 }}>{w.count}</div>
                    <div
                      style={{
                        width: '100%',
                        maxWidth: 40,
                        height: `${Math.round(((w.count || 0) / maxWeekly) * 100)}%`,
                        minHeight: 2,
                        background: 'var(--accent)',
                        borderRadius: '4px 4px 0 0',
                      }}
                    />
                    <div className="muted" style={{ fontSize: 10, marginTop: 6, textAlign: 'center' }}>{w.week}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {distSection(t('Por tipo'), byType)}
          {distSection(t('Por prioridade'), byPriority)}

          <div className="card">
            <h4 style={{ margin: '0 0 12px', color: 'var(--muted)' }}>{t("Por projeto")}</h4>
            {perProject.length === 0 && <div className="muted">{t("Nenhum projeto.")}</div>}
            {perProject.map((p) => (
              <div
                key={p.projectId}
                className="row"
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}
              >
                <span>
                  <b>{p.projectKey}</b> · {p.projectName}
                </span>
                <span className="muted">
                  {p.doneTasks}/{p.totalTasks}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
