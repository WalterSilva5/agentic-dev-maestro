import { useEffect, useState } from 'react'
import {
  getTask,
  updateTask,
  getComments,
  addComment,
  addChecklist,
  toggleChecklist,
  deleteChecklist,
  getMembers,
  createMember,
} from '../api'
import { apiError } from '../api'
import { t, tf } from '../i18n'

const TYPES = ['FEATURE', 'BUG', 'TECH_DEBT', 'IMPROVEMENT', 'CHORE']
const PRIOS = ['LOW', 'MEDIUM', 'HIGH', 'URGENT']

export default function TaskDetail({ code, onClose, onChanged }) {
  const [task, setTask] = useState(null)
  const [comments, setComments] = useState([])
  const [newComment, setNewComment] = useState('')
  const [newCheck, setNewCheck] = useState('')
  const [error, setError] = useState('')
  const [members, setMembers] = useState([])
  const [newAssignee, setNewAssignee] = useState('')
  const [showNewAssignee, setShowNewAssignee] = useState(false)

  const load = async () => {
    try {
      const t = await getTask(code)
      setTask(t)
      setComments(await getComments(t.id))
      if (t.projectId) {
        try { setMembers(await getMembers(t.projectId)) } catch { setMembers([]) }
      }
    } catch (e) { setError(String(e.message || e)) }
  }

  useEffect(() => {
    load()
  }, [code])

  const patch = async (body) => {
    try {
      await updateTask(code, body)
      await load()
      onChanged?.()
    } catch (e) {
      setError(apiError(e))
    }
  }

  const assignMember = async (name) => {
    const val = (name || '').trim() || null
    try {
      if (val && task?.projectId) {
        try { await createMember(task.projectId, { name: val }) } catch {}
        try { setMembers(await getMembers(task.projectId)) } catch {}
      }
      await patch({ assignee: val })
    } catch (e) { setError(String(e.message || e)) }
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

        <label style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 8, fontSize: 12, cursor: 'pointer' }}
          title={t('Card que existe só aqui: o sync do board externo não cria, não atualiza e não apaga.')}>
          <input type="checkbox" style={{ width: 'auto' }} checked={!!task.isLocal}
            onChange={(e) => patch({ isLocal: e.target.checked })} />
          {t('Tarefa local (não sincroniza)')}
        </label>

        <div className="section">
          <h4>{t('Responsável')}</h4>
          <div className="row" style={{ gap: 8, alignItems: 'center' }}>
            <select value={task.assignee || ''} onChange={(e) => { const v=e.target.value; if(v==='__new__') setShowNewAssignee(true); else assignMember(v) }} style={{ flex: 1 }}>
              <option value="">{t('Sem responsável')}</option>
              {members.map((m) => (<option key={m.id} value={m.name}>{m.name}</option>))}
              {task.assignee && !members.some((m)=>m.name===task.assignee) && (<option value={task.assignee}>{task.assignee} (legado)</option>)}
              <option value="__new__">{t('+ Novo responsável...')}</option>
            </select>
            {task.assignee && (
              <span style={{ width: 28, height: 28, borderRadius: 14, background: members.find((m)=>m.name===task.assignee)?.color || 'var(--accent)', color: '#fff', display: 'grid', placeItems: 'center', fontSize: 11, fontWeight: 700 }} title={task.assignee}>
                {task.assignee.split(' ').slice(0,2).map((p)=>p[0]?.toUpperCase()).join('') || '?'}
              </span>
            )}
          </div>
          {showNewAssignee && (
            <div className="row" style={{ marginTop: 8 }}>
              <input placeholder={t('Nome do responsável...')} value={newAssignee} onChange={(e)=>setNewAssignee(e.target.value)} style={{ flex: 1 }} onKeyDown={async (e)=>{ if(e.key==='Enter' && newAssignee.trim()){ await assignMember(newAssignee.trim()); setNewAssignee(''); setShowNewAssignee(false) }}} />
              <button onClick={async()=>{ if(!newAssignee.trim()) return; await assignMember(newAssignee.trim()); setNewAssignee(''); setShowNewAssignee(false)}}>{t('Atribuir')}</button>
              <button className="ghost" onClick={()=>setShowNewAssignee(false)}>{t('Cancelar')}</button>
            </div>
          )}
          <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>{t('Facilita filtro e métricas por pessoa.')}</div>
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
