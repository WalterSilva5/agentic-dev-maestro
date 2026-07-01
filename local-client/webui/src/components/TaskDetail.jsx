import { useEffect, useState } from 'react'
import {
  getTask,
  updateTask,
  getComments,
  addComment,
  addChecklist,
  toggleChecklist,
  deleteChecklist,
} from '../api'
import { t, tf } from '../i18n'

const TYPES = ['FEATURE', 'BUG', 'TECH_DEBT', 'IMPROVEMENT', 'CHORE']
const PRIOS = ['LOW', 'MEDIUM', 'HIGH', 'URGENT']

export default function TaskDetail({ code, onClose, onChanged }) {
  const [task, setTask] = useState(null)
  const [comments, setComments] = useState([])
  const [newComment, setNewComment] = useState('')
  const [newCheck, setNewCheck] = useState('')
  const [error, setError] = useState('')

  const load = () =>
    Promise.all([getTask(code), null])
      .then(async () => {
        const t = await getTask(code)
        setTask(t)
        setComments(await getComments(t.id))
      })
      .catch((e) => setError(String(e.message || e)))

  useEffect(() => {
    load()
  }, [code])

  const patch = async (body) => {
    try {
      await updateTask(code, body)
      await load()
      onChanged?.()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const submitComment = async () => {
    if (!newComment.trim()) return
    await addComment(task.id, newComment.trim())
    setNewComment('')
    setComments(await getComments(task.id))
  }

  const submitCheck = async () => {
    if (!newCheck.trim()) return
    await addChecklist(code, newCheck.trim())
    setNewCheck('')
    load()
  }

  if (!task) {
    return (
      <div className="overlay" onClick={onClose}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          {error ? <div className="banner">{error}</div> : <div className="muted">{t('Carregando...')}</div>}
        </div>
      </div>
    )
  }

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button className="close-x" onClick={onClose}>✕</button>
        <div className="muted" style={{ fontSize: 11, fontWeight: 700 }}>{task.code}</div>
        <h2>{task.title}</h2>

        {error && <div className="banner">{error}</div>}

        <div className="row" style={{ marginTop: 8 }}>
          <select value={task.type} onChange={(e) => patch({ type: e.target.value })}>
            {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <select value={task.priority} onChange={(e) => patch({ priority: e.target.value })}>
            {PRIOS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>

        <div className="section">
          <h4>{t('Descrição')}</h4>
          <textarea
            style={{ width: '100%', minHeight: 90 }}
            defaultValue={task.description || ''}
            onBlur={(e) => e.target.value !== (task.description || '') && patch({ description: e.target.value })}
          />
        </div>

        <div className="section">
          <h4>{t('Checklist')}</h4>
          {(task.checklist || []).map((c) => (
            <div key={c.id} className={`check-item ${c.checked ? 'done' : ''}`}>
              <input type="checkbox" checked={c.checked} onChange={() => toggleChecklist(c.id).then(load)} />
              <span style={{ flex: 1 }}>{c.title}</span>
              <button className="ghost" style={{ padding: '2px 6px', fontSize: 11 }} onClick={() => deleteChecklist(c.id).then(load)}>✕</button>
            </div>
          ))}
          <div className="row" style={{ marginTop: 6 }}>
            <input
              placeholder={t('Novo item...')}
              style={{ flex: 1 }}
              value={newCheck}
              onChange={(e) => setNewCheck(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && submitCheck()}
            />
            <button className="ghost" onClick={submitCheck}>+</button>
          </div>
        </div>

        <div className="section">
          <h4>{tf('Comentários ({n})', { n: comments.length })}</h4>
          {comments.map((c) => (
            <div key={c.id} className="comment">
              <div className="meta">{c.type} · {c.author || 'local'}</div>
              <div>{c.body}</div>
            </div>
          ))}
          <div className="row" style={{ marginTop: 6 }}>
            <input
              placeholder={t('Comentário...')}
              style={{ flex: 1 }}
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && submitComment()}
            />
            <button onClick={submitComment}>{t('Enviar')}</button>
          </div>
        </div>
      </div>
    </div>
  )
}
