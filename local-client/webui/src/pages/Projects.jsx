import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getProjects, createProject } from '../api'
import { t } from '../i18n'

export default function Projects() {
  const [projects, setProjects] = useState([])
  const [name, setName] = useState('')
  const [key, setKey] = useState('')
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
      await createProject({ name: name.trim(), key: key.trim().toUpperCase() })
      setName('')
      setKey('')
      setError('')
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
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
        <button onClick={onCreate}>{t('+ Criar projeto')}</button>
      </div>

      <div className="projects-grid">
        {projects.map((p) => (
          <div key={p.id} className="card project-card" onClick={() => nav(`/board/${p.id}`)}>
            <div className="key">{p.key}</div>
            <div className="pname">{p.name}</div>
            <div className="desc">{p.description || t('Sem descrição')}</div>
          </div>
        ))}
        {projects.length === 0 && <div className="muted">{t('Nenhum projeto ainda.')}</div>}
      </div>
    </div>
  )
}
