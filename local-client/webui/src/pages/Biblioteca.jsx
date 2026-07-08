import { useEffect, useState } from 'react'
import {
  getSnippets,
  createSnippet,
  updateSnippet,
  useSnippet,
  deleteSnippet,
  getRunbooks,
  createRunbook,
  updateRunbook,
  useRunbook,
  deleteRunbook,
  scanTodos,
  importTodos,
  getProjects,
} from '../api'
import { t } from '../i18n'

const EMPTY_SNIPPET = { title: '', kind: 'SNIPPET', language: '', tags: '', content: '' }
const EMPTY_RUNBOOK = { title: '', category: '', command: '', description: '' }

function copy(text) {
  if (navigator.clipboard) navigator.clipboard.writeText(text || '')
}

function SnippetsTab() {
  const [items, setItems] = useState([])
  const [q, setQ] = useState('')
  const [kind, setKind] = useState('')
  const [form, setForm] = useState(EMPTY_SNIPPET)
  const [editing, setEditing] = useState(null)

  const load = () =>
    getSnippets({ ...(kind ? { kind } : {}), ...(q ? { q } : {}) }).then(setItems).catch(() => {})

  useEffect(() => {
    load()
  }, [q, kind])

  const save = async () => {
    if (!form.title.trim()) return
    if (editing) await updateSnippet(editing, form)
    else await createSnippet(form)
    setForm(EMPTY_SNIPPET)
    setEditing(null)
    load()
  }

  const startEdit = (s) => {
    setEditing(s.id)
    setForm({ title: s.title, kind: s.kind, language: s.language, tags: s.tags, content: s.content })
  }

  return (
    <div>
      <div className="card">
        <div className="toolbar">
          <input placeholder={t('Título')} value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
            <option value="SNIPPET">{t('Snippet')}</option>
            <option value="PROMPT">{t('Prompt')}</option>
          </select>
          <input placeholder={t('Linguagem (ex.: bash, python)')} value={form.language}
            onChange={(e) => setForm({ ...form, language: e.target.value })} />
          <input placeholder={t('Tags separadas por vírgula')} value={form.tags}
            onChange={(e) => setForm({ ...form, tags: e.target.value })} />
        </div>
        <textarea rows={5} placeholder={t('Conteúdo...')} value={form.content} style={{ width: '100%', marginTop: 8 }}
          onChange={(e) => setForm({ ...form, content: e.target.value })} />
        <div className="row" style={{ gap: 8, marginTop: 8 }}>
          <button onClick={save}>{editing ? t('Salvar') : t('+ Novo')}</button>
          {editing && (
            <button className="ghost" onClick={() => { setEditing(null); setForm(EMPTY_SNIPPET) }}>
              {t('Cancelar')}
            </button>
          )}
        </div>
      </div>

      <div className="toolbar" style={{ marginTop: 16 }}>
        <input placeholder={t('Buscar...')} value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="">{t('Todos')}</option>
          <option value="SNIPPET">{t('Snippet')}</option>
          <option value="PROMPT">{t('Prompt')}</option>
        </select>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        {items.map((s) => (
          <div key={s.id} className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600 }}>
                {s.kind === 'SNIPPET' ? '🧩' : '💬'} {s.title}
                <span className="muted" style={{ marginLeft: 8, fontSize: 12 }}>
                  {[s.language, s.tags].filter(Boolean).join(' · ')}
                </span>
              </div>
              <pre style={{ margin: '4px 0 0', whiteSpace: 'pre-wrap', fontSize: 12, opacity: 0.8, maxHeight: 60, overflow: 'hidden' }}>{s.content}</pre>
            </div>
            <div className="row" style={{ gap: 6 }}>
              <button onClick={() => { copy(s.content); useSnippet(s.id) }}>{t('Copiar')}</button>
              <button className="ghost" onClick={() => startEdit(s)}>✎</button>
              <button className="danger" onClick={() => deleteSnippet(s.id).then(load)}>✕</button>
            </div>
          </div>
        ))}
        {items.length === 0 && <div className="muted">{t('Nada aqui ainda.')}</div>}
      </div>
    </div>
  )
}

function RunbooksTab() {
  const [items, setItems] = useState([])
  const [q, setQ] = useState('')
  const [form, setForm] = useState(EMPTY_RUNBOOK)
  const [editing, setEditing] = useState(null)

  const load = () => getRunbooks(q ? { q } : {}).then(setItems).catch(() => {})
  useEffect(() => {
    load()
  }, [q])

  const save = async () => {
    if (!form.title.trim()) return
    if (editing) await updateRunbook(editing, form)
    else await createRunbook(form)
    setForm(EMPTY_RUNBOOK)
    setEditing(null)
    load()
  }
  const startEdit = (r) => {
    setEditing(r.id)
    setForm({ title: r.title, category: r.category, command: r.command, description: r.description })
  }

  return (
    <div>
      <div className="card">
        <div className="toolbar">
          <input placeholder={t('Título')} value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <input placeholder={t('Categoria (ex.: setup, deploy)')} value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })} />
        </div>
        <textarea rows={2} placeholder={t('Comando(s)...')} value={form.command} style={{ width: '100%', marginTop: 8, fontFamily: 'monospace' }}
          onChange={(e) => setForm({ ...form, command: e.target.value })} />
        <textarea rows={2} placeholder={t('Descrição (opcional)')} value={form.description} style={{ width: '100%', marginTop: 8 }}
          onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <div className="row" style={{ gap: 8, marginTop: 8 }}>
          <button onClick={save}>{editing ? t('Salvar') : t('+ Novo')}</button>
          {editing && (
            <button className="ghost" onClick={() => { setEditing(null); setForm(EMPTY_RUNBOOK) }}>
              {t('Cancelar')}
            </button>
          )}
        </div>
      </div>

      <div className="toolbar" style={{ marginTop: 16 }}>
        <input placeholder={t('Buscar...')} value={q} onChange={(e) => setQ(e.target.value)} />
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        {items.map((r) => (
          <div key={r.id} className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600 }}>
                ⚙️ {r.title}
                {r.category && <span className="muted" style={{ marginLeft: 8, fontSize: 12 }}>{r.category}</span>}
              </div>
              <code style={{ fontSize: 12, opacity: 0.85 }}>{r.command}</code>
              {r.description && <div className="muted" style={{ fontSize: 12 }}>{r.description}</div>}
            </div>
            <div className="row" style={{ gap: 6 }}>
              <button onClick={() => { copy(r.command); useRunbook(r.id) }}>{t('Copiar comando')}</button>
              <button className="ghost" onClick={() => startEdit(r)}>✎</button>
              <button className="danger" onClick={() => deleteRunbook(r.id).then(load)}>✕</button>
            </div>
          </div>
        ))}
        {items.length === 0 && <div className="muted">{t('Nada aqui ainda.')}</div>}
      </div>
    </div>
  )
}

function ImportTab() {
  const [path, setPath] = useState('')
  const [items, setItems] = useState([])
  const [selected, setSelected] = useState({})
  const [projects, setProjects] = useState([])
  const [projectId, setProjectId] = useState('')
  const [status, setStatus] = useState('')

  useEffect(() => {
    getProjects().then((ps) => {
      setProjects(ps)
      if (ps[0]) setProjectId(String(ps[0].id))
    }).catch(() => {})
  }, [])

  const scan = async () => {
    if (!path.trim()) return
    setStatus(t('Varrendo...'))
    try {
      const r = await scanTodos({ path: path.trim() })
      setItems(r.items)
      const sel = {}
      r.items.forEach((_, i) => { sel[i] = true })
      setSelected(sel)
      setStatus(`${t('Encontrados')}: ${r.count}`)
    } catch (e) {
      setStatus(e.response?.data?.detail || String(e.message || e))
    }
  }

  const doImport = async () => {
    if (!projectId) return setStatus(t('Selecione um projeto'))
    const chosen = items.filter((_, i) => selected[i])
    if (!chosen.length) return setStatus(t('Nada selecionado'))
    const r = await importTodos({ projectId: Number(projectId), items: chosen })
    setStatus(`${t('Tarefas criadas')}: ${r.created}`)
    setItems([])
    setSelected({})
  }

  return (
    <div>
      <p className="subtitle">{t('Varre uma pasta por TODO/FIXME/HACK/XXX e cria tarefas no projeto escolhido.')}</p>
      <div className="card">
        <div className="toolbar">
          <input style={{ flex: 1 }} placeholder={t('Pasta do repositório...')} value={path}
            onChange={(e) => setPath(e.target.value)} />
          <button onClick={scan}>{t('Varrer')}</button>
        </div>
        <div className="toolbar" style={{ marginTop: 8 }}>
          <span>{t('Projeto:')}</span>
          <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.key} — {p.name}</option>
            ))}
          </select>
          <button onClick={doImport} disabled={!items.length}>{t('Importar selecionados')}</button>
        </div>
        {status && <div className="muted" style={{ marginTop: 8 }}>{status}</div>}
      </div>

      {items.length > 0 && (
        <div className="card" style={{ marginTop: 12, maxHeight: 400, overflow: 'auto' }}>
          {items.map((it, i) => (
            <label key={i} className="row" style={{ gap: 8, padding: '4px 0', cursor: 'pointer' }}>
              <input type="checkbox" checked={!!selected[i]}
                onChange={(e) => setSelected({ ...selected, [i]: e.target.checked })} />
              <span style={{ fontSize: 13 }}>
                <b>[{it.marker}]</b> <span className="muted">{it.file}:{it.line}</span> — {it.text}
              </span>
            </label>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Biblioteca() {
  const [tab, setTab] = useState('snippets')
  const tabs = [
    ['snippets', t('Snippets & Prompts')],
    ['runbooks', t('Runbooks')],
    ['import', t('Importar do código')],
  ]
  return (
    <div>
      <h1 className="page-title">{t('Biblioteca')}</h1>
      <p className="subtitle">{t('Snippets, prompts, comandos e importação de TODO/FIXME')}</p>
      <div className="row" style={{ gap: 8, marginBottom: 12 }}>
        {tabs.map(([k, label]) => (
          <button key={k} className={tab === k ? '' : 'ghost'} onClick={() => setTab(k)}>{label}</button>
        ))}
      </div>
      {tab === 'snippets' && <SnippetsTab />}
      {tab === 'runbooks' && <RunbooksTab />}
      {tab === 'import' && <ImportTab />}
    </div>
  )
}
