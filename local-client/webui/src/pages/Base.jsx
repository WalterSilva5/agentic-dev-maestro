import { useEffect, useState } from 'react'
import { getKbNotes, createKbNote, updateKbNote, deleteKbNote, kbAsk } from '../api'
import { t } from '../i18n'

const EMPTY = { title: '', body: '' }

export default function Base() {
  const [notes, setNotes] = useState([])
  const [q, setQ] = useState('')
  const [sel, setSel] = useState(null) // id em edição
  const [form, setForm] = useState(EMPTY)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState(null)
  const [asking, setAsking] = useState(false)
  const [error, setError] = useState('')

  const load = () => getKbNotes(q ? { q } : {}).then(setNotes).catch((e) => setError(String(e.message || e)))
  useEffect(() => {
    load()
  }, [q])

  const openNew = () => { setSel(null); setForm(EMPTY) }
  const openNote = (n) => { setSel(n.id); setForm({ title: n.title, body: n.body }) }

  const save = async () => {
    if (!form.title.trim()) return
    try {
      if (sel) await updateKbNote(sel, form)
      else {
        const created = await createKbNote(form)
        setSel(created.id)
      }
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const remove = async (id) => {
    await deleteKbNote(id)
    if (sel === id) openNew()
    load()
  }

  const ask = async () => {
    if (!question.trim()) return
    setAsking(true)
    setAnswer(null)
    try {
      const r = await kbAsk({ question })
      setAnswer(r)
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    } finally {
      setAsking(false)
    }
  }

  const current = notes.find((n) => n.id === sel)

  return (
    <div>
      <h1 className="page-title">{t('Base de conhecimento')}</h1>
      <p className="subtitle">{t('Notas com backlinks [[título]] e perguntas respondidas pela IA sobre as suas notas.')}</p>
      {error && <div className="banner">{error}</div>}

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="toolbar">
          <input style={{ flex: 1 }} placeholder={t('Pergunte à sua base...')} value={question}
            onChange={(e) => setQuestion(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && ask()} />
          <button onClick={ask} disabled={asking}>{asking ? t('Pensando...') : t('Perguntar à IA')}</button>
        </div>
        {answer && (
          <div style={{ marginTop: 10, fontSize: 13 }}>
            <div style={{ whiteSpace: 'pre-wrap' }}>{answer.answer}</div>
            {answer.sources?.length > 0 && (
              <div className="muted" style={{ marginTop: 6 }}>
                {t('Fontes')}: {answer.sources.map((sc) => sc.title).join(', ')}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="row" style={{ gap: 16, alignItems: 'flex-start' }}>
        <div style={{ flex: 1, minWidth: 200 }}>
          <div className="toolbar" style={{ marginBottom: 8 }}>
            <input style={{ flex: 1 }} placeholder={t('Buscar...')} value={q} onChange={(e) => setQ(e.target.value)} />
            <button onClick={openNew}>{t('+ Nova')}</button>
          </div>
          <div className="card">
            {notes.map((n) => (
              <div key={n.id} className="row" style={{ justifyContent: 'space-between', alignItems: 'center', padding: '4px 0' }}>
                <span style={{ cursor: 'pointer', fontWeight: sel === n.id ? 700 : 400 }} onClick={() => openNote(n)}>
                  {n.title}
                  {n.backlinks?.length > 0 && <span className="muted" style={{ fontSize: 11 }}> ↩{n.backlinks.length}</span>}
                </span>
                <button className="danger" onClick={() => remove(n.id)}>✕</button>
              </div>
            ))}
            {notes.length === 0 && <div className="muted">{t('Nenhuma nota ainda.')}</div>}
          </div>
        </div>

        <div style={{ flex: 2, minWidth: 0 }}>
          <div className="card">
            <input style={{ width: '100%', fontWeight: 600 }} placeholder={t('Título da nota')} value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })} />
            <textarea rows={14} style={{ width: '100%', marginTop: 8 }} placeholder={t('Conteúdo... use [[título]] para linkar outra nota')}
              value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} />
            <div className="row" style={{ gap: 8, marginTop: 8 }}>
              <button onClick={save}>{sel ? t('Salvar') : t('Criar nota')}</button>
              {sel && <button className="ghost" onClick={openNew}>{t('+ Nova')}</button>}
            </div>
            {current?.backlinks?.length > 0 && (
              <div className="muted" style={{ marginTop: 8, fontSize: 12 }}>
                {t('Referenciada por')}: {current.backlinks.map((b) => b.title).join(', ')}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
