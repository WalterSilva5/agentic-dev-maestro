import { useEffect, useState } from 'react'
import { getLabels, createLabel, deleteLabel } from '../api'
import { t } from '../i18n'

const PALETTE = [
  '#E03131', '#E8590C', '#2F9E44', '#1971C2',
  '#6741D9', '#C2255C', '#4C6EF5', '#0CA678',
  '#F08C00', '#0C8599', '#66A80F', '#868E96',
]

export default function Labels() {
  const [labels, setLabels] = useState([])
  const [name, setName] = useState('')
  const [color, setColor] = useState(PALETTE[0])
  const [error, setError] = useState('')

  const load = () =>
    getLabels().then(setLabels).catch((e) => setError(String(e.message || e)))

  useEffect(() => {
    load()
  }, [])

  const onCreate = async () => {
    if (!name.trim()) return
    try {
      await createLabel(name.trim(), color)
      setName('')
      setColor(PALETTE[0])
      setError('')
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const onDelete = async (id) => {
    try {
      await deleteLabel(id)
      setError('')
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  return (
    <div>
      <h1 className="page-title">{t('Labels')}</h1>
      <p className="subtitle">{t('Organize suas tarefas com labels coloridas.')}</p>

      {error && <div className="banner">{error}</div>}

      <div className="card">
        <div className="toolbar">
          <input
            placeholder={t('Nome da label')}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button onClick={onCreate}>{t('Criar label')}</button>
        </div>

        <div className="row" style={{ flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
          {PALETTE.map((c) => (
            <div
              key={c}
              onClick={() => setColor(c)}
              style={{
                width: 24,
                height: 24,
                borderRadius: 6,
                background: c,
                cursor: 'pointer',
                border: color === c ? '2px solid var(--text)' : '2px solid transparent',
                outline: color === c ? '1px solid var(--text)' : 'none',
              }}
            />
          ))}
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        {labels.map((l) => (
          <div
            key={l.id}
            className="row"
            style={{ alignItems: 'center', justifyContent: 'space-between', padding: '6px 0' }}
          >
            <div className="row" style={{ alignItems: 'center', gap: 8 }}>
              <span
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  background: l.color,
                  display: 'inline-block',
                }}
              />
              <span>{l.name}</span>
            </div>
            <button className="danger" onClick={() => onDelete(l.id)}>{t('Excluir')}</button>
          </div>
        ))}
        {labels.length === 0 && <div className="muted">{t('Nenhuma label ainda.')}</div>}
      </div>
    </div>
  )
}
