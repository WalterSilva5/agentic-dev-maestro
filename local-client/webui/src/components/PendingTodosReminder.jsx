import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getPendingTodos, snoozeTodo } from '../api'
import { t, tf } from '../i18n'

// Lembrete periódico (só na interface) de TODOs cujo horário já chegou.
export default function PendingTodosReminder() {
  const [pending, setPending] = useState({ count: 0, items: [] })
  const [dismissed, setDismissed] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    const poll = () =>
      getPendingTodos()
        .then((p) => {
          setPending(p || { count: 0, items: [] })
          setDismissed(false) // reaparece a cada ciclo enquanto houver pendentes
        })
        .catch(() => {})
    poll()
    const id = setInterval(poll, 60000) // a cada 1 min
    return () => clearInterval(id)
  }, [])

  if (!pending.count || dismissed) return null

  const snoozeAll = async () => {
    try {
      await Promise.all((pending.items || []).map((it) => snoozeTodo(it.id, 10)))
    } catch {
      /* ignore */
    }
    setPending({ count: 0, items: [] })
  }

  return (
    <div
      style={{
        position: 'fixed',
        right: 20,
        bottom: 20,
        zIndex: 1000,
        background: 'var(--card, #fff)',
        border: '1px solid var(--warning, #d97706)',
        borderRadius: 10,
        padding: '10px 12px',
        boxShadow: '0 6px 20px rgba(20,22,60,0.18)',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        maxWidth: 420,
      }}
    >
      <span style={{ fontWeight: 600 }}>
        ⏰ {tf('{n} tarefa(s) pendente(s)', { n: pending.count })}
      </span>
      <button
        onClick={() => {
          setDismissed(true)
          navigate('/todos')
        }}
      >
        {t('Ver')}
      </button>
      <button className="ghost" onClick={snoozeAll}>
        {t('Adiar 10min')}
      </button>
      <button className="ghost" onClick={() => setDismissed(true)} title={t('Dispensar')}>
        ✕
      </button>
    </div>
  )
}
