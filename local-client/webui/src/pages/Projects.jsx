import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getProjects, createProject, updateProject } from '../api'
import { t } from '../i18n'

export default function Projects() {
  const [projects, setProjects] = useState([])
  const [name, setName] = useState('')
  const [key, setKey] = useState('')
  const [azureUrl, setAzureUrl] = useState('')
  const [error, setError] = useState('')
  const nav = useNavigate()

  const load = () =>
    getProjects().then(setProjects).catch((e) => setError(String(e.message || e)))

  useEffect(() => {
    load()
  }, [])

  const onCreate = async () => {
    if (!name.trim() || !key.trim()) return
    try {
      const body = { name: name.trim(), key: key.trim().toUpperCase() }
      if (azureUrl.trim()) body.azureBoardUrl = azureUrl.trim()
      await createProject(body)
      setName('')
      setKey('')
      setAzureUrl('')
      setError('')
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const onSetAzure = async (p) => {
    const cur = p.azureBoardUrl || ''
    const val = window.prompt(t('Link do board do Azure (cole a URL):'), cur)
    if (val === null) return
    try {
      await updateProject(p.id, { azureBoardUrl: val.trim() })
      load()
    } catch (e) { setError(String(e.message || e)) }
  }

  return (
    <div>
      <h1 className="page-title">{t('Projetos')}</h1>
      <p className="subtitle">{t('Web UI servida pela própria API do Maestro.')}</p>

      {error && <div className="banner">{error}</div>}

      <div className="toolbar">
        <input placeholder={t('Nome do projeto')} value={name} onChange={(e) => setName(e.target.value)} />
        <input
          placeholder={t('Chave (ex: DEMO)')}
          value={key}
          style={{ width: 130 }}
          onChange={(e) => setKey(e.target.value)}
        />
        <input
          placeholder={t('Link do board Azure (opcional)')}
          value={azureUrl}
          style={{ flex: 1, minWidth: 220 }}
          onChange={(e) => setAzureUrl(e.target.value)}
        />
        <button onClick={onCreate}>{t('+ Criar projeto')}</button>
      </div>

      <div className="projects-grid">
        {projects.map((p) => (
          <div key={p.id} className="card project-card" onClick={() => nav(`/board/${p.id}`)} style={{ position: 'relative' }}>
            <div className="key">{p.key}</div>
            <div className="pname">{p.name}</div>
            <div className="desc">{p.description || t('Sem descrição')}</div>
            <div className="row" style={{ marginTop: 8, gap: 6 }} onClick={(e)=>e.stopPropagation()}>
              {p.azureBoardUrl ? (
                <a href={p.azureBoardUrl} target="_blank" rel="noreferrer" className="badge-type" style={{ textDecoration: 'none' }} title={p.azureBoardUrl}>🔗 Azure Board ↗</a>
              ) : (
                <span className="muted" style={{ fontSize: 11 }}>{t('Sem link Azure')}</span>
              )}
              <button className="ghost" style={{ marginLeft: 'auto', padding: '2px 8px', fontSize: 11 }} onClick={()=>onSetAzure(p)}>{p.azureBoardUrl ? t('Editar link') : t('Definir link')}</button>
            </div>
          </div>
        ))}
        {projects.length === 0 && <div className="muted">{t('Nenhum projeto ainda.')}</div>}
      </div>
    </div>
  )
}
