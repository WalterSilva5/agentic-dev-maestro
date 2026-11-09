import { useEffect, useState } from 'react'
import {
  getCoachConfig, getSettings, putCoachConfig, updateSettings,
  createBackup, listBackups, backupDownloadUrl,
} from '../api'
import { getTheme, toggleTheme } from '../theme'
import { t } from '../i18n'

export default function Configuracoes() {
  const [settings, setSettings] = useState(null)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState('')
  const [selectedProviderId, setSelectedProviderId] = useState('')
  const [coach, setCoach] = useState(null)
  // aparência
  const [tema, setTema] = useState(getTheme())
  // backup do banco (quem copia é a API; a tela só dispara e mostra)
  const [backupando, setBackupando] = useState(false)
  const [backups, setBackups] = useState([])
  const [backupDir, setBackupDir] = useState('')
  const [ultimoBackup, setUltimoBackup] = useState(null)

  useEffect(() => {
    getSettings()
      .then((s) => {
        setSettings(s)
        setSelectedProviderId(s.activeProviderId)
      })
      .catch((e) => setError(e?.message || t('Erro ao carregar configurações')))
    getCoachConfig()
      .then(setCoach)
      .catch(() => setCoach({ enabled: true, interval_min: 90 }))
    carregarBackups()
  }, [])

  const carregarBackups = async () => {
    try {
      const d = await listBackups()
      setBackups(d.backups || [])
      setBackupDir(d.dir || '')
    } catch {
      /* sem backup ainda é normal */
    }
  }

  const trocarTema = () => setTema(toggleTheme())

  const fazerBackup = async () => {
    setBackupando(true)
    setError('')
    try {
      const d = await createBackup()
      setUltimoBackup(d.backups?.[0] || null)
      await carregarBackups()
      flash(t('Backup concluído'))
    } catch (e) {
      const detalhe = e?.response?.data?.detail
      setError(typeof detalhe === 'string' ? detalhe : (e?.message || t('Falha no backup')))
    } finally {
      setBackupando(false)
    }
  }

  const tamanho = (bytes) => {
    const kb = (bytes || 0) / 1024
    return kb > 1024 ? `${(kb / 1024).toFixed(2)} MB` : `${Math.round(kb)} KB`
  }

  const saveCoach = async (patch) => {
    try {
      const updated = await putCoachConfig({ ...coach, ...patch })
      setCoach(updated)
      flash(t('Configuração salva'))
    } catch (e) {
      setError(e?.message || t('Erro ao salvar configurações'))
    }
  }

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
      setError(e?.message || t('Erro ao salvar configurações'))
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
        <h1 className="page-title">{t('Configurações')}</h1>
        {error && <div className="banner">{error}</div>}
        {!error && <p className="muted">{t('Carregando...')}</p>}
      </div>
    )
  }

  const current = settings.aiProviders.find((p) => p.id === selectedProviderId) || settings.aiProviders[0]

  return (
    <div>
      <h1 className="page-title">{t('Configurações')}</h1>
      <p className="subtitle">{t('Idioma, provedores de IA e transcrições')}</p>

      {error && <div className="banner">{error}</div>}
      {saved && <p className="muted">{saved}</p>}

      <div className="card">
        <h4 style={{ color: 'var(--muted)' }}>🎨 {t('Aparência')}</h4>
        <div className="row" style={{ gap: 8, alignItems: 'center' }}>
          <span className="muted">{t('Tema atual:')} <b>{tema === 'dark' ? t('Escuro') : t('Claro')}</b></span>
          <button className="ghost" onClick={trocarTema}>
            {tema === 'dark' ? `☀ ${t('Usar tema claro')}` : `☾ ${t('Usar tema escuro')}`}
          </button>
        </div>
      </div>

      <div className="card">
        <h4 style={{ color: 'var(--muted)' }}>💾 {t('Backup do banco')}</h4>
        <p className="muted" style={{ marginTop: 0 }}>
          {t('A API copia o banco do workspace ativo para a pasta de backup do servidor. Nada é gravado pelo navegador.')}
        </p>
        <div className="row" style={{ gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <button onClick={fazerBackup} disabled={backupando}>
            {backupando ? `⏳ ${t('Fazendo backup...')}` : `💾 ${t('Fazer backup agora')}`}
          </button>
          {backupDir && <span className="muted" style={{ fontSize: 11 }}>{t('Destino:')} <code>{backupDir}</code></span>}
        </div>

        {ultimoBackup && (
          <p className="muted" style={{ fontSize: 12, marginBottom: 0 }}>
            {t('Último backup:')} <b>{ultimoBackup.file}</b> · {tamanho(ultimoBackup.bytes)}
          </p>
        )}

        {backups.length > 0 && (
          <div style={{ marginTop: 10 }}>
            <div className="muted" style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: .5, marginBottom: 4 }}>
              {t('Últimos backups')}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {backups.slice(0, 5).map((b) => (
                <div key={b.file} className="row" style={{ gap: 8, alignItems: 'center', fontSize: 12 }}>
                  <span>{(b.createdAt || '').replace('T', ' ')}</span>
                  <span className="muted">{tamanho(b.bytes)}</span>
                  <code style={{ fontSize: 11 }}>{b.file}</code>
                  <span style={{ flex: 1 }} />
                  <a href={backupDownloadUrl(b.file)} download>{t('Baixar')}</a>
                </div>
              ))}
            </div>
          </div>
        )}
        {backups.length === 0 && <p className="muted" style={{ fontSize: 12 }}>{t('Nenhum backup ainda.')}</p>}
      </div>

      <div className="card">
        <h4 style={{ color: 'var(--muted)' }}>{t('Idioma')}</h4>
        <div className="row">
          <select
            value={settings.language}
            onChange={async (e) => {
              await apply({ language: e.target.value })
              window.location.reload()
            }}
          >
            <option value="pt">{t('Português')}</option>
            <option value="en">{t('English')}</option>
          </select>
        </div>
        <p className="muted">{t('Também afeta o app desktop (após reiniciar).')}</p>
      </div>

      <div className="card">
        <h4 style={{ color: 'var(--muted)' }}>{t('Provedores de IA')}</h4>
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
                placeholder={t('Nome')}
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
                t('Provedores salvos')
              )
            }
          >
            {t('Salvar')}
          </button>
        </div>
      </div>

      <div className="card">
        <h4 style={{ color: 'var(--muted)' }}>{t('Reuniões')}</h4>
        <div className="row">
          <select
            value={settings.whisperModel}
            onChange={(e) => apply({ whisperModel: e.target.value }, t('Modelo salvo'))}
          >
            <option value="tiny">tiny</option>
            <option value="base">base</option>
            <option value="small">small</option>
            <option value="medium">medium</option>
            <option value="large-v3">large-v3</option>
          </select>
        </div>

        <div className="row" style={{ gap: 10, marginTop: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <span className="muted" style={{ fontSize: 11, fontWeight: 700 }}>
            {t('Contexto do copiloto (board e dailies):')}
          </span>
          {[
            ['cards', t('cards parados')],
            ['overdue', t('atrasados')],
            ['dailies', t('dailies')],
          ].map(([campo, rotulo]) => (
            <label key={campo} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
              <input
                type="number" min="1" max="50" style={{ width: 64 }}
                value={(settings.meetingContext || {})[campo] ?? ''}
                onChange={(e) => apply({
                  meetingContext: { ...(settings.meetingContext || {}), [campo]: Number(e.target.value) },
                })}
              />
              {rotulo}
            </label>
          ))}
        </div>
        <p className="muted" style={{ marginBottom: 0, fontSize: 11 }}>
          {t('Quanto do projeto entra no contexto da reunião: cards em andamento (mais parados), atrasados e registros recentes da daily.')}
        </p>
      </div>

      {coach && (
        <div className="card">
          <h4 style={{ color: 'var(--muted)' }}>💡 {t('Coach proativo')}</h4>
          <p className="muted" style={{ marginTop: 0 }}>
            {t('O agente dá dicas curtas e acionáveis ao longo do dia, com base no seu board e TODOs. Requer um provedor de IA ativo.')}
          </p>
          <label className="row" style={{ gap: 8, alignItems: 'center' }}>
            <input
              type="checkbox"
              checked={coach.enabled !== false}
              onChange={(e) => saveCoach({ enabled: e.target.checked })}
            />
            {t('Ativar dicas proativas do agente')}
          </label>
          <div className="row" style={{ gap: 8, alignItems: 'center', marginTop: 8 }}>
            <span>{t('Intervalo (minutos):')}</span>
            <input
              type="number"
              min="15"
              max="480"
              style={{ width: 90 }}
              value={coach.interval_min || 90}
              onChange={(e) => setCoach({ ...coach, interval_min: Number(e.target.value) })}
              onBlur={(e) => saveCoach({ interval_min: Number(e.target.value) })}
            />
          </div>
        </div>
      )}
    </div>
  )
}
