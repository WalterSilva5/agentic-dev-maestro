import { useState } from 'react'
import { translateText } from '../api'
import { t } from '../i18n'

const LANGS = [
  ['pt', 'Português'],
  ['en', 'Inglês'],
  ['es', 'Espanhol'],
  ['fr', 'Francês'],
  ['de', 'Alemão'],
  ['it', 'Italiano'],
  ['ja', 'Japonês'],
  ['zh', 'Chinês'],
  ['ko', 'Coreano'],
  ['ru', 'Russo'],
]

export default function Traducao() {
  const [source, setSource] = useState('auto')
  const [target, setTarget] = useState('en')
  const [input, setInput] = useState('')
  const [output, setOutput] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)

  const swap = () => {
    const newSource = target
    const newTarget = source === 'auto' ? 'en' : source
    setSource(newSource)
    setTarget(newTarget)
    setInput(output)
    setOutput(input)
  }

  const run = async () => {
    if (!input.trim()) return
    setLoading(true)
    setStatus(t('Traduzindo...'))
    try {
      const r = await translateText({ text: input, source, target })
      setOutput(r.translated || '')
      setStatus(source === 'auto' && r.detectedSource ? `${t('Detectado')}: ${r.detectedSource}` : '')
    } catch (e) {
      setStatus(e.response?.data?.detail || String(e.message || e))
    } finally {
      setLoading(false)
    }
  }

  const copy = () => {
    if (output && navigator.clipboard) {
      navigator.clipboard.writeText(output)
      setStatus(t('Copiado!'))
    }
  }

  return (
    <div>
      <h1 className="page-title">{t('Tradutor')}</h1>
      <p className="subtitle">{t('Traduza texto entre idiomas (detecção automática da origem).')}</p>

      <div className="toolbar" style={{ marginBottom: 10, alignItems: 'center' }}>
        <select value={source} onChange={(e) => setSource(e.target.value)}>
          <option value="auto">{t('Detectar idioma')}</option>
          {LANGS.map(([c, l]) => <option key={c} value={c}>{t(l)}</option>)}
        </select>
        <button className="ghost" onClick={swap} title={t('Trocar idiomas')}>⇄</button>
        <select value={target} onChange={(e) => setTarget(e.target.value)}>
          {LANGS.map(([c, l]) => <option key={c} value={c}>{t(l)}</option>)}
        </select>
      </div>

      <div className="row" style={{ gap: 12, alignItems: 'stretch' }}>
        <textarea
          style={{ flex: 1, minHeight: 220 }}
          placeholder={t('Digite o texto...')}
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <textarea
          style={{ flex: 1, minHeight: 220 }}
          placeholder={t('Tradução')}
          value={output}
          readOnly
        />
      </div>

      <div className="row" style={{ gap: 8, marginTop: 10, alignItems: 'center' }}>
        <button onClick={run} disabled={loading}>{loading ? t('Traduzindo...') : t('Traduzir')}</button>
        <button className="ghost" onClick={copy}>{t('Copiar')}</button>
        {status && <span className="muted">{status}</span>}
      </div>
    </div>
  )
}
