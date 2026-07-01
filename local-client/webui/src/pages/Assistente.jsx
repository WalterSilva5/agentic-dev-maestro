import { useState, useRef, useEffect } from 'react'
import { assistantChat } from '../api'
import { t } from '../i18n'

const SUGGESTIONS = [
  'Resuma o board e o que priorizar hoje',
  'Solicite revisão das tarefas em Fazendo',
  'Crie um TODO com os riscos que você identificar',
]

export default function Assistente() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const scrollRef = useRef(null)

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, loading])

  async function send(text) {
    const content = (text ?? input).trim()
    if (!content || loading) return

    const history = [...messages, { role: 'user', content }]
    setMessages(history)
    setInput('')
    setError('')
    setLoading(true)

    try {
      const { reply } = await assistantChat(history)
      setMessages([...history, { role: 'assistant', content: reply }])
    } catch (err) {
      const detail =
        err?.response?.data?.detail ||
        err?.message ||
        t('Falha ao falar com o assistente.')
      setError(detail)
    } finally {
      setLoading(false)
    }
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div>
      <div className="page-title">{t('Assistente')}</div>
      <div className="subtitle">
        {t(
          'Converse com o assistente interno: ele lê o board, sugere prioridades, solicita revisões, cria TODOs e comenta tarefas.'
        )}
      </div>

      {error && <div className="banner">{error}</div>}

      <div
        className="toolbar"
        style={{ display: 'flex', flexWrap: 'wrap', gap: 8, margin: '12px 0' }}
      >
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            className="ghost"
            onClick={() => send(s)}
            disabled={loading}
          >
            {t(s)}
          </button>
        ))}
      </div>

      <div className="card">
        <div
          ref={scrollRef}
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
            maxHeight: '55vh',
            overflowY: 'auto',
            paddingRight: 4,
          }}
        >
          {messages.length === 0 && !loading && (
            <div className="muted">
              {t(
                'Nenhuma mensagem ainda. Faça uma pergunta ou use uma sugestão acima.'
              )}
            </div>
          )}

          {messages.map((m, i) => {
            const isUser = m.role === 'user'
            return (
              <div
                key={i}
                style={{
                  display: 'flex',
                  justifyContent: isUser ? 'flex-end' : 'flex-start',
                }}
              >
                <div
                  style={{
                    maxWidth: '78%',
                    padding: '8px 12px',
                    borderRadius: 12,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    background: isUser ? 'var(--accent)' : 'var(--card)',
                    color: isUser ? '#fff' : 'inherit',
                    border: isUser ? 'none' : '1px solid var(--border)',
                  }}
                >
                  {m.content}
                </div>
              </div>
            )
          })}

          {loading && (
            <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
              <div
                className="muted"
                style={{
                  maxWidth: '78%',
                  padding: '8px 12px',
                  borderRadius: 12,
                  background: 'var(--card)',
                  border: '1px solid var(--border)',
                }}
              >
                {t('Pensando...')}
              </div>
            </div>
          )}
        </div>

        <div
          className="row"
          style={{ display: 'flex', gap: 8, marginTop: 12 }}
        >
          <input
            style={{ flex: 1 }}
            placeholder={t('Escreva sua mensagem...')}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={loading}
          />
          <button onClick={() => send()} disabled={loading || !input.trim()}>
            {t('Enviar')}
          </button>
        </div>
      </div>
    </div>
  )
}
