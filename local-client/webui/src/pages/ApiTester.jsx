import { useEffect, useState } from 'react'
import {
  getApiRequests,
  createApiRequest,
  updateApiRequest,
  deleteApiRequest,
  runApiRequest,
  getApiHistory,
} from '../api'
import { t } from '../i18n'

const METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
const EMPTY = { name: '', method: 'GET', url: '', headers: '', body: '' }

export default function ApiTester() {
  const [saved, setSaved] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [editing, setEditing] = useState(null)
  const [resp, setResp] = useState(null)
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState([])
  const [status, setStatus] = useState('')

  const loadSaved = () => getApiRequests().then(setSaved).catch(() => {})
  const loadHistory = () => getApiHistory({ limit: 20 }).then(setHistory).catch(() => {})

  useEffect(() => {
    loadSaved()
    loadHistory()
  }, [])

  const run = async () => {
    if (!form.url.trim()) return
    setLoading(true)
    setResp(null)
    try {
      const r = await runApiRequest({
        method: form.method, url: form.url, headers: form.headers,
        body: form.body, requestId: editing || undefined,
      })
      setResp(r)
      loadHistory()
    } catch (e) {
      setStatus(e.response?.data?.detail || String(e.message || e))
    } finally {
      setLoading(false)
    }
  }

  const save = async () => {
    if (!form.name.trim() || !form.url.trim()) return setStatus(t('Informe nome e URL'))
    if (editing) await updateApiRequest(editing, form)
    else {
      const created = await createApiRequest(form)
      setEditing(created.id)
    }
    setStatus(t('Salvo'))
    loadSaved()
  }

  const load = (r) => {
    setEditing(r.id)
    setForm({ name: r.name, method: r.method, url: r.url, headers: r.headers, body: r.body })
    setResp(null)
  }

  const remove = async (id) => {
    await deleteApiRequest(id)
    if (editing === id) { setEditing(null); setForm(EMPTY) }
    loadSaved()
  }

  return (
    <div>
      <h1 className="page-title">{t('Testador de API')}</h1>
      <p className="subtitle">{t('Monte, execute e salve requisições HTTP (mini-Postman).')}</p>

      <div className="row" style={{ gap: 16, alignItems: 'flex-start' }}>
        <div style={{ flex: 2, minWidth: 0 }}>
          <div className="card">
            <div className="toolbar">
              <select value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value })}>
                {METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
              <input style={{ flex: 1 }} placeholder="https://..." value={form.url}
                onChange={(e) => setForm({ ...form, url: e.target.value })} />
              <button onClick={run} disabled={loading}>{loading ? t('Executando...') : t('Executar')}</button>
            </div>
            <input style={{ width: '100%', marginTop: 8 }} placeholder={t('Nome para salvar')}
              value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <textarea rows={3} style={{ width: '100%', marginTop: 8, fontFamily: 'monospace' }}
              placeholder={t('Headers (JSON ou "Chave: valor" por linha)')}
              value={form.headers} onChange={(e) => setForm({ ...form, headers: e.target.value })} />
            <textarea rows={4} style={{ width: '100%', marginTop: 8, fontFamily: 'monospace' }}
              placeholder={t('Corpo (body)')}
              value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} />
            <div className="row" style={{ gap: 8, marginTop: 8 }}>
              <button onClick={save}>{editing ? t('Atualizar') : t('Salvar')}</button>
              {editing && <button className="ghost" onClick={() => { setEditing(null); setForm(EMPTY) }}>{t('Novo')}</button>}
              {status && <span className="muted">{status}</span>}
            </div>
          </div>

          {resp && (
            <div className="card" style={{ marginTop: 12 }}>
              <div className="row" style={{ gap: 12, alignItems: 'center' }}>
                <span style={{
                  fontWeight: 700,
                  color: resp.ok ? 'var(--success, #2f9e44)' : 'var(--danger, #e5484d)',
                }}>
                  {resp.status ?? t('Erro')}
                </span>
                <span className="muted">{resp.durationMs} ms</span>
              </div>
              {resp.error && <div className="banner" style={{ marginTop: 8 }}>{resp.error}</div>}
              <pre style={{ marginTop: 8, whiteSpace: 'pre-wrap', wordBreak: 'break-word', maxHeight: 360, overflow: 'auto', fontSize: 12 }}>{resp.body}</pre>
            </div>
          )}
        </div>

        <div style={{ flex: 1, minWidth: 200 }}>
          <div className="card">
            <b>{t('Salvos')}</b>
            {saved.map((r) => (
              <div key={r.id} className="row" style={{ justifyContent: 'space-between', alignItems: 'center', padding: '4px 0' }}>
                <span style={{ cursor: 'pointer', fontSize: 13 }} onClick={() => load(r)}>
                  <b>{r.method}</b> {r.name}
                </span>
                <button className="danger" onClick={() => remove(r.id)}>✕</button>
              </div>
            ))}
            {saved.length === 0 && <div className="muted">{t('Nenhum request salvo.')}</div>}
          </div>

          <div className="card" style={{ marginTop: 12 }}>
            <b>{t('Histórico')}</b>
            {history.map((h) => (
              <div key={h.id} style={{ padding: '4px 0', fontSize: 12, borderBottom: '1px solid var(--border)' }}>
                <span style={{ color: h.ok ? 'var(--success, #2f9e44)' : 'var(--danger, #e5484d)', fontWeight: 700 }}>
                  {h.status ?? 'ERR'}
                </span>{' '}
                <b>{h.method}</b> <span className="muted">{h.durationMs}ms</span>
                <div className="muted" style={{ wordBreak: 'break-all' }}>{h.url}</div>
              </div>
            ))}
            {history.length === 0 && <div className="muted">{t('Sem histórico.')}</div>}
          </div>
        </div>
      </div>
    </div>
  )
}
