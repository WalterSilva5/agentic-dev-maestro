import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCoachConfig, getCoachTip } from '../api'
import { t } from '../i18n'

// Coach proativo: busca uma dica curta e acionável do agente ao longo do dia
// (a mesma do desktop) e a exibe num card não intrusivo no canto inferior.
export default function CoachTip() {
  const [tip, setTip] = useState(null) // { tip, category }
  const [dismissed, setDismissed] = useState(false)
  const navigate = useNavigate()
  const timerRef = useRef(null)
  const recentRef = useRef([])

  useEffect(() => {
    let cancelled = false

    const fetchTip = async () => {
      try {
        const data = await getCoachTip()
        const text = (data && data.tip ? String(data.tip) : '').trim()
        if (cancelled || !text) return
        if (recentRef.current.includes(text)) return // evita repetir a mesma dica
        recentRef.current = [...recentRef.current, text].slice(-5)
        setTip({ tip: text, category: (data.category || '').trim() })
        setDismissed(false)
      } catch {
        /* sem provedor / erro: silencioso */
      }
    }

    const schedule = async () => {
      let intervalMin = 90
      let enabled = true
      try {
        const cfg = await getCoachConfig()
        enabled = cfg?.enabled !== false
        intervalMin = Math.max(15, Number(cfg?.interval_min) || 90)
      } catch {
        /* usa defaults */
      }
      if (cancelled || !enabled) return
      // Primeira dica pouco depois de abrir; depois no intervalo configurado.
      const first = setTimeout(fetchTip, 90000)
      timerRef.current = setInterval(fetchTip, intervalMin * 60000)
      return () => clearTimeout(first)
    }

    const cleanupFirst = schedule()
    return () => {
      cancelled = true
      if (timerRef.current) clearInterval(timerRef.current)
      Promise.resolve(cleanupFirst).then((fn) => typeof fn === 'function' && fn())
    }
  }, [])

  if (!tip || dismissed) return null

  return (
    <div
      style={{
        position: 'fixed',
        right: 20,
        bottom: 20,
        zIndex: 1000,
        background: 'var(--card, #fff)',
        border: '1px solid var(--accent, #6366f1)',
        borderLeft: '4px solid var(--accent, #6366f1)',
        borderRadius: 10,
        padding: '10px 14px 12px',
        boxShadow: '0 6px 20px rgba(20,22,60,0.18)',
        maxWidth: 360,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <strong>
          💡 {t('Dica do agente')}
          {tip.category ? `  ·  ${tip.category}` : ''}
        </strong>
        <span style={{ flex: 1 }} />
        <button className="ghost" onClick={() => setDismissed(true)} title={t('Dispensar')}>
          ✕
        </button>
      </div>
      <div style={{ fontSize: 13, color: 'var(--muted, #555)', lineHeight: 1.4 }}>{tip.tip}</div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
        <button
          className="ghost"
          onClick={() => {
            setDismissed(true)
            navigate('/assistente')
          }}
        >
          {t('Abrir Assistente')}
        </button>
      </div>
    </div>
  )
}
