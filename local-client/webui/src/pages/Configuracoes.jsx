import { useEffect, useState } from 'react'
import { getSettings, updateSettings } from '../api'

export default function Configuracoes() {
  const [settings, setSettings] = useState(null)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState('')
  const [selectedProviderId, setSelectedProviderId] = useState('')

  useEffect(() => {
    getSettings()
      .then((s) => {
        setSettings(s)
        setSelectedProviderId(s.activeProviderId)
      })
      .catch((e) => setError(e?.message || 'Erro ao carregar configurações'))
  }, [])

  const flash = (msg) => {
    setSaved(msg)
    setTimeout(() => setSaved(''), 2000)
  }

  const apply = async (patch, okMsg) => {
    setError('')
    try {
      const updated = await updateSettings(patch)
      setSettings(updated)
      if (updated.activeProviderId != null) setSelectedProviderId(updated.activeProviderId)
      if (okMsg) flash(okMsg)
    } catch (e) {
      setError(e?.message || 'Erro ao salvar configurações')
    }
  }

  const editProvider = (id, field, value) => {
    setSettings((prev) => ({
      ...prev,
      aiProviders: prev.aiProviders.map((p) => (p.id === id ? { ...p, [field]: value } : p)),
    }))
  }

  if (!settings) {
    return (
      <div>
        <h1 className="page-title">Configurações</h1>
        {error && <div className="banner">{error}</div>}
        {!error && <p className="muted">Carregando...</p>}
      </div>
    )
  }

  const current = settings.aiProviders.find((p) => p.id === selectedProviderId) || settings.aiProviders[0]

  return (
    <div>
      <h1 className="page-title">Configurações</h1>
      <p className="subtitle">Idioma, provedores de IA e transcrições</p>

      {error && <div className="banner">{error}</div>}
      {saved && <p className="muted">{saved}</p>}

      <div className="card">
        <h4 style={{ color: 'var(--muted)' }}>Idioma</h4>
        <div className="row">
          <select
            value={settings.language}
            onChange={(e) => apply({ language: e.target.value }, 'Idioma salvo')}
          >
            <option value="pt">Português</option>
            <option value="en">English</option>
          </select>
        </div>
        <p className="muted">Afeta o app desktop; a web ainda é PT.</p>
      </div>

      <div className="card">
        <h4 style={{ color: 'var(--muted)' }}>Provedores de IA</h4>
        <div className="row">
          <select
            value={selectedProviderId}
            onChange={(e) => setSelectedProviderId(e.target.value)}
          >
            {settings.aiProviders.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        {current && (
          <>
            <div className="row">
              <input
                type="text"
                placeholder="Nome"
                value={current.name || ''}
                onChange={(e) => editProvider(current.id, 'name', e.target.value)}
              />
            </div>
            <div className="row">
              <input
                type="text"
                placeholder="Base URL"
                value={current.base_url || ''}
                onChange={(e) => editProvider(current.id, 'base_url', e.target.value)}
              />
            </div>
            <div className="row">
              <input
                type="password"
                placeholder="API Key"
                value={current.api_key || ''}
                onChange={(e) => editProvider(current.id, 'api_key', e.target.value)}
              />
            </div>
            <div className="row">
              <input
                type="text"
                placeholder="Model"
                value={current.model || ''}
                onChange={(e) => editProvider(current.id, 'model', e.target.value)}
              />
            </div>
          </>
        )}

        <div className="row">
          <button
            onClick={() =>
              apply(
                { aiProviders: settings.aiProviders, activeProviderId: selectedProviderId },
                'Provedores salvos'
              )
            }
          >
            Salvar
          </button>
        </div>
      </div>

      <div className="card">
        <h4 style={{ color: 'var(--muted)' }}>Transcrições</h4>
        <div className="row">
          <select
            value={settings.whisperModel}
            onChange={(e) => apply({ whisperModel: e.target.value }, 'Modelo salvo')}
          >
            <option value="tiny">tiny</option>
            <option value="base">base</option>
            <option value="small">small</option>
            <option value="medium">medium</option>
            <option value="large-v3">large-v3</option>
          </select>
        </div>
      </div>
    </div>
  )
}
