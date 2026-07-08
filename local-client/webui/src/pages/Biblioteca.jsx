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
  triageBug,
  codeReview,
  gitStatus,
  getTimeLogs,
  logTime,
  deleteTimeLog,
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

function TriageTab() {
  const [text, setText] = useState('')
  const [triage, setTriage] = useState(null)
  const [projects, setProjects] = useState([])
  const [projectId, setProjectId] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getProjects().then((ps) => {
      setProjects(ps)
      if (ps[0]) setProjectId(String(ps[0].id))
    }).catch(() => {})
  }, [])

  const run = async () => {
    if (!text.trim()) return
    setLoading(true)
    setStatus(t('Triando...'))
    setTriage(null)
    try {
      const r = await triageBug({ text })
      setTriage(r.triage)
      setStatus('')
    } catch (e) {
      setStatus(e.response?.data?.detail || String(e.message || e))
    } finally {
      setLoading(false)
    }
  }

  const createTask = async () => {
    if (!projectId) return setStatus(t('Selecione um projeto'))
    try {
      const r = await triageBug({ text, projectId: Number(projectId), create: true })
      setStatus(`${t('Tarefa criada')}: ${r.task?.code || ''}`)
    } catch (e) {
      setStatus(e.response?.data?.detail || String(e.message || e))
    }
  }

  return (
    <div>
      <p className="subtitle">{t('Cole um stacktrace/relato. A IA classifica e você cria uma tarefa BUG.')}</p>
      <div className="card">
        <textarea rows={6} placeholder={t('Cole aqui o stacktrace ou a descrição do problema...')}
          value={text} style={{ width: '100%', fontFamily: 'monospace' }}
          onChange={(e) => setText(e.target.value)} />
        <div className="row" style={{ gap: 8, marginTop: 8 }}>
          <button onClick={run} disabled={loading}>{t('Triar com IA')}</button>
        </div>
      </div>

      {triage && (
        <div className="card" style={{ marginTop: 12 }}>
          <div style={{ fontWeight: 600 }}>{triage.title}</div>
          <div className="muted" style={{ margin: '4px 0' }}>
            {t('Severidade')}: <b>{triage.severity}</b> · {t('Prioridade')}: <b>{triage.priority}</b>
          </div>
          {triage.summary && <div>{triage.summary}</div>}
          {triage.probable_cause && <div style={{ marginTop: 4 }}><b>{t('Causa provável')}:</b> {triage.probable_cause}</div>}
          {triage.steps?.length > 0 && (
            <ul>{triage.steps.map((s, i) => <li key={i}>{s}</li>)}</ul>
          )}
          <div className="row" style={{ gap: 8, marginTop: 8, alignItems: 'center' }}>
            <span>{t('Projeto:')}</span>
            <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.key} — {p.name}</option>)}
            </select>
            <button onClick={createTask}>{t('Criar tarefa BUG')}</button>
          </div>
        </div>
      )}
      {status && <div className="muted" style={{ marginTop: 8 }}>{status}</div>}
    </div>
  )
}

function CodeReviewTab() {
  const [path, setPath] = useState('')
  const [base, setBase] = useState('')
  const [taskCode, setTaskCode] = useState('')
  const [review, setReview] = useState(null)
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)

  const run = async (post) => {
    if (!path.trim()) return setStatus(t('Informe o caminho do repositório'))
    setLoading(true)
    setStatus(t('Revisando...'))
    try {
      const r = await codeReview({
        path, base, taskCode: post && taskCode.trim() ? taskCode.trim() : undefined,
      })
      setReview(r.review)
      setStatus(r.posted ? `${t('Comentário postado na tarefa')}` : '')
    } catch (e) {
      setStatus(e.response?.data?.detail || String(e.message || e))
    } finally {
      setLoading(false)
    }
  }

  const sevColor = (s) => s === 'HIGH' ? 'var(--danger, #e5484d)' : s === 'MEDIUM' ? 'var(--warning, #f08c00)' : 'var(--muted)'

  return (
    <div>
      <p className="subtitle">{t('Aponte um repositório e uma base (branch/ref). A IA revisa o diff.')}</p>
      <div className="card">
        <input style={{ width: '100%' }} placeholder={t('Pasta do repositório...')} value={path}
          onChange={(e) => setPath(e.target.value)} />
        <div className="toolbar" style={{ marginTop: 8 }}>
          <input style={{ flex: 1 }} placeholder={t('Base (ex.: main, HEAD~1) — vazio = alterações locais')} value={base}
            onChange={(e) => setBase(e.target.value)} />
          <input style={{ width: 140 }} placeholder={t('Tarefa (ex.: PROJ-1)')} value={taskCode}
            onChange={(e) => setTaskCode(e.target.value)} />
        </div>
        <div className="row" style={{ gap: 8, marginTop: 8 }}>
          <button onClick={() => run(false)} disabled={loading}>{loading ? t('Revisando...') : t('Revisar com IA')}</button>
          <button className="ghost" onClick={() => run(true)} disabled={loading || !taskCode.trim()}>{t('Revisar e comentar na tarefa')}</button>
          {status && <span className="muted">{status}</span>}
        </div>
      </div>

      {review && (
        <div className="card" style={{ marginTop: 12, fontSize: 13 }}>
          {review.summary && <p style={{ marginTop: 0 }}>{review.summary}</p>}
          {review.issues?.length > 0 && (
            <div>
              <b>{t('Problemas')}</b>
              <ul style={{ margin: '2px 0 8px' }}>
                {review.issues.map((it, i) => (
                  <li key={i}><b style={{ color: sevColor(it.severity) }}>[{it.severity}]</b> {it.file && <code>{it.file}</code>} — {it.note}</li>
                ))}
              </ul>
            </div>
          )}
          {review.suggestions?.length > 0 && (
            <div><b>{t('Sugestões')}</b><ul style={{ margin: '2px 0' }}>{review.suggestions.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
          )}
          {review.truncated && <div className="muted">{t('(diff truncado para revisão)')}</div>}
        </div>
      )}
    </div>
  )
}

function GitTab() {
  const [path, setPath] = useState('')
  const [st, setSt] = useState(null)
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)

  const load = async () => {
    if (!path.trim()) return setStatus(t('Informe o caminho do repositório'))
    setLoading(true)
    setStatus('')
    try {
      const r = await gitStatus(path.trim(), true)
      setSt(r)
    } catch (e) {
      setStatus(e.response?.data?.detail || String(e.message || e))
      setSt(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <p className="subtitle">{t('Estado do repositório: branch, mudanças, commits e PRs (via gh).')}</p>
      <div className="card">
        <div className="toolbar">
          <input style={{ flex: 1 }} placeholder={t('Pasta do repositório...')} value={path}
            onChange={(e) => setPath(e.target.value)} />
          <button onClick={load} disabled={loading}>{loading ? t('Carregando...') : t('Atualizar')}</button>
        </div>
        {status && <div className="muted" style={{ marginTop: 8 }}>{status}</div>}
      </div>

      {st && (
        <div className="card" style={{ marginTop: 12, fontSize: 13 }}>
          <div className="row" style={{ gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <span><b>🌿 {st.branch}</b></span>
            <span className="muted">↑{st.ahead} ↓{st.behind}</span>
            <span style={{ color: st.clean ? 'var(--success, #2f9e44)' : 'var(--warning, #f08c00)' }}>
              {st.clean ? t('Limpo') : t('Com alterações')}
            </span>
          </div>

          {(st.staged?.length > 0 || st.unstaged?.length > 0 || st.untracked?.length > 0) && (
            <div style={{ marginTop: 8 }}>
              {st.staged?.length > 0 && <div><b>{t('Staged')}</b><ul style={{ margin: '2px 0 6px' }}>{st.staged.map((x, i) => <li key={i}><code>{x}</code></li>)}</ul></div>}
              {st.unstaged?.length > 0 && <div><b>{t('Não-staged')}</b><ul style={{ margin: '2px 0 6px' }}>{st.unstaged.map((x, i) => <li key={i}><code>{x}</code></li>)}</ul></div>}
              {st.untracked?.length > 0 && <div><b>{t('Não rastreados')}</b><ul style={{ margin: '2px 0 6px' }}>{st.untracked.map((x, i) => <li key={i}><code>{x}</code></li>)}</ul></div>}
            </div>
          )}

          {st.prs?.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <b>{t('Pull requests')}</b>
              <ul style={{ margin: '2px 0 6px' }}>
                {st.prs.map((p) => (
                  <li key={p.number}><a href={p.url} target="_blank" rel="noreferrer">#{p.number}</a> {p.title} <span className="muted">({p.branch})</span></li>
                ))}
              </ul>
            </div>
          )}

          <div style={{ marginTop: 8 }}>
            <b>{t('Commits recentes')}</b>
            <ul style={{ margin: '2px 0' }}>
              {st.commits.map((c, i) => (
                <li key={i}><code>{c.hash}</code> {c.subject} <span className="muted">— {c.author}, {c.when}</span></li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}

function fmtDur(sec) {
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = sec % 60
  return h > 0 ? `${h}h${String(m).padStart(2, '0')}` : `${m}m${String(s).padStart(2, '0')}s`
}

function TimeTab() {
  const [data, setData] = useState({ logs: [], weekSeconds: 0, weekByTask: [] })
  const [running, setRunning] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [taskCode, setTaskCode] = useState('')
  const [note, setNote] = useState('')
  const [minutes, setMinutes] = useState('')

  const load = () => getTimeLogs(50).then(setData).catch(() => {})
  useEffect(() => {
    load()
  }, [])

  useEffect(() => {
    if (!running) return undefined
    const id = setInterval(() => setElapsed((e) => e + 1), 1000)
    return () => clearInterval(id)
  }, [running])

  const stop = async () => {
    setRunning(false)
    if (elapsed > 0) {
      await logTime({ seconds: elapsed, taskCode: taskCode.trim() || undefined, note })
      load()
    }
    setElapsed(0)
  }

  const logManual = async () => {
    const mins = parseInt(minutes, 10)
    if (!mins || mins <= 0) return
    await logTime({ seconds: mins * 60, taskCode: taskCode.trim() || undefined, note })
    setMinutes('')
    load()
  }

  return (
    <div>
      <p className="subtitle">{t('Cronômetro e registro de tempo por tarefa. Total da semana e por tarefa.')}</p>
      <div className="card">
        <div className="toolbar">
          <input placeholder={t('Tarefa (ex.: PROJ-1)')} value={taskCode} onChange={(e) => setTaskCode(e.target.value)} style={{ width: 140 }} />
          <input placeholder={t('Nota (opcional)')} value={note} onChange={(e) => setNote(e.target.value)} style={{ flex: 1 }} />
        </div>
        <div className="row" style={{ gap: 12, marginTop: 10, alignItems: 'center' }}>
          <span style={{ fontSize: 24, fontFamily: 'monospace' }}>{fmtDur(elapsed)}</span>
          {!running
            ? <button onClick={() => setRunning(true)}>{t('Iniciar')}</button>
            : <button className="danger" onClick={stop}>{t('Parar e registrar')}</button>}
          <span className="muted">|</span>
          <input placeholder={t('min')} value={minutes} onChange={(e) => setMinutes(e.target.value)} style={{ width: 70 }} />
          <button className="ghost" onClick={logManual}>{t('Registrar manual')}</button>
        </div>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <b>{t('Esta semana')}: {fmtDur(data.weekSeconds)}</b>
        {data.weekByTask.length > 0 && (
          <ul style={{ margin: '6px 0' }}>
            {data.weekByTask.map((r) => (
              <li key={r.taskCode}><b>{r.taskCode}</b> — {fmtDur(r.seconds)}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <b>{t('Registros recentes')}</b>
        {data.logs.map((l) => (
          <div key={l.id} className="row" style={{ justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', fontSize: 13 }}>
            <span>{fmtDur(l.seconds)} {l.taskCode && <b>· {l.taskCode}</b>} {l.note && <span className="muted">— {l.note}</span>}</span>
            <button className="danger" onClick={() => deleteTimeLog(l.id).then(load)}>✕</button>
          </div>
        ))}
        {data.logs.length === 0 && <div className="muted">{t('Nenhum registro ainda.')}</div>}
      </div>
    </div>
  )
}

export default function Biblioteca() {
  const [tab, setTab] = useState('snippets')
  const tabs = [
    ['snippets', t('Snippets & Prompts')],
    ['runbooks', t('Runbooks')],
    ['import', t('Importar do código')],
    ['triage', t('Triagem de bugs')],
    ['review', t('Code review')],
    ['git', t('Git')],
    ['time', t('Tempo')],
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
      {tab === 'triage' && <TriageTab />}
      {tab === 'review' && <CodeReviewTab />}
      {tab === 'git' && <GitTab />}
      {tab === 'time' && <TimeTab />}
    </div>
  )
}
