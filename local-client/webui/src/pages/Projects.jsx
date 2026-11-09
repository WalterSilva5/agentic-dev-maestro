import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Swal from 'sweetalert2'
import { getProjects, createProject, updateProject, moveProject, getWorkspaces } from '../api'
import { t } from '../i18n'

export default function Projects() {
  const [projects, setProjects] = useState([])
  const [name, setName] = useState('')
  const [key, setKey] = useState('')
  const [boardUrl, setBoardUrl] = useState('')
  const [error, setError] = useState('')
  const [workspaces, setWorkspaces] = useState([])
  const nav = useNavigate()

  const load = () =>
    getProjects().then(setProjects).catch((e) => setError(String(e.message || e)))

  const loadWorkspaces = () =>
    getWorkspaces().then((r) => setWorkspaces(r.workspaces || r)).catch(() => {})

  useEffect(() => {
    load()
    loadWorkspaces()
  }, [])

  const onCreate = async () => {
    if (!name.trim() || !key.trim()) return
    try {
      const body = { name: name.trim(), key: key.trim().toUpperCase() }
      if (boardUrl.trim()) body.boardUrl = boardUrl.trim()
      await createProject(body)
      setName('')
      setKey('')
      setBoardUrl('')
      setError('')
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const onSetBoard = async (p) => {
    const cur = p.boardUrl || ''
    const { value: val } = await Swal.fire({
      title: t('Link do board externo (cole a URL):'),
      input: 'url',
      inputValue: cur,
      inputPlaceholder: 'https://...',
      showCancelButton: true,
      confirmButtonText: t('Salvar'),
      cancelButtonText: t('Cancelar'),
    })
    if (val === undefined) return
    try {
      await updateProject(p.id, { boardUrl: (val || '').trim() })
      load()
    } catch (e) { setError(String(e.message || e)) }
  }

  const onSetTarget = async (p) => {
    const { value: val } = await Swal.fire({
      title: t('Previsão de entrega do projeto:'),
      input: 'date',
      inputValue: (p.targetDate || '').slice(0, 10),
      showCancelButton: true,
      confirmButtonText: t('Salvar'),
      cancelButtonText: t('Cancelar'),
    })
    if (val === undefined) return
    try {
      await updateProject(p.id, { targetDate: val || null })
      load()
    } catch (e) { setError(String(e.message || e)) }
  }

  const onMove = async (p) => {
    if (workspaces.length <= 1) {
      await Swal.fire({ icon: 'info', title: t('Crie outro workspace antes de mover.') })
      return
    }
    const { value: tid } = await Swal.fire({
      title: t('Mover para workspace'),
      html: `<p>${t('Mover o projeto')} "<b>${p.name}</b>" (${p.key})</p>`,
      input: 'select',
      inputOptions: Object.fromEntries(workspaces.map((w) => [w.id, `${w.id}: ${w.name}`])),
      inputPlaceholder: t('Selecione um workspace'),
      showCancelButton: true,
      confirmButtonText: t('Mover'),
      cancelButtonText: t('Cancelar'),
      inputValidator: (v) => (!v ? t('Selecione um workspace') : null),
    })
    if (!tid) return
    const confirm = await Swal.fire({
      title: t('Confirmar mover'),
      text: `${t('Mover o projeto')} "${p.name}" (${p.key}) ${t('para o workspace')} "${tid}"?`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: t('Mover'),
      cancelButtonText: t('Cancelar'),
    })
    if (!confirm.isConfirmed) return
    try {
      await moveProject(p.id, tid)
      load()
      Swal.fire({ icon: 'success', title: t('Projeto movido'), timer: 1500, showConfirmButton: false })
    } catch (e) { setError(e.response?.data?.detail || String(e.message || e)) }
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
          placeholder={t('Link do board externo (opcional)')}
          value={boardUrl}
          style={{ flex: 1, minWidth: 220 }}
          onChange={(e) => setBoardUrl(e.target.value)}
        />
        <button onClick={onCreate}>{t('+ Criar projeto')}</button>
      </div>

      <div className="projects-grid">
        {projects.map((p) => (
          <div key={p.id} className="card project-card" onClick={() => nav(`/board/${p.id}`)} style={{ position: 'relative' }}>
            <div className="key">{p.key}</div>
            <div className="pname">{p.name}</div>
            <div className="desc">{p.description || t('Sem descrição')}</div>
            {p.targetDate && <div className="muted" style={{ fontSize: 11 }}>{t('Previsão de entrega')}: {p.targetDate.slice(0, 10).split('-').reverse().join('/')}</div>}
            <div className="row" style={{ marginTop: 8, gap: 6 }} onClick={(e)=>e.stopPropagation()}>
              {p.boardUrl ? (
                <a href={p.boardUrl} target="_blank" rel="noreferrer" className="badge-type" style={{ textDecoration: 'none' }} title={p.boardUrl}>🔗 Board ↗</a>
              ) : (
                <span className="muted" style={{ fontSize: 11 }}>{t('Sem link do board')}</span>
              )}
              <button className="ghost" style={{ padding: '2px 8px', fontSize: 11 }} onClick={()=>onSetTarget(p)}>{p.targetDate ? t('Editar previsão') : t('Definir previsão')}</button>
              <button className="ghost" style={{ marginLeft: 'auto', padding: '2px 8px', fontSize: 11 }} onClick={()=>onSetBoard(p)}>{p.boardUrl ? t('Editar link') : t('Definir link')}</button>
              <button className="ghost" style={{ padding: '2px 8px', fontSize: 11 }} onClick={()=>onMove(p)} title={t('Mover para outro workspace')}>↗ {t('Mover')}</button>
            </div>
          </div>
        ))}
        {projects.length === 0 && <div className="muted">{t('Nenhum projeto ainda.')}</div>}
      </div>
    </div>
  )
}
