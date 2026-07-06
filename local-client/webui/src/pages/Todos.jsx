import { useEffect, useState } from 'react'
import { getTodos, addTodo, updateTodo, deleteTodo } from '../api'
import { t, tf } from '../i18n'

const PRIORITIES = [
  ['LOW', 'Baixa'],
  ['MEDIUM', 'Média'],
  ['HIGH', 'Alta'],
]

const RECURRENCES = [
  ['NONE', 'Não repete'],
  ['DAILY', 'Diária'],
  ['WEEKLY', 'Semanal'],
  ['MONTHLY', 'Mensal'],
]

// ISO local (sem fuso) para o input datetime-local (também usado para exibir)
function toLocalInput(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export default function Todos() {
  const [todos, setTodos] = useState([])
  const [text, setText] = useState('')
  const [priority, setPriority] = useState('MEDIUM')
  const [recurrence, setRecurrence] = useState('NONE')
  const [dueAt, setDueAt] = useState('')
  const [error, setError] = useState('')

  const load = () =>
    getTodos().then(setTodos).catch((e) => setError(String(e.message || e)))

  useEffect(() => {
    load()
  }, [])

  const onAdd = async () => {
    if (!text.trim()) return
    try {
      await addTodo({ text: text.trim(), priority, recurrence, dueAt: dueAt || null })
      setText('')
      setDueAt('')
      setPriority('MEDIUM')
      setRecurrence('NONE')
      setError('')
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  // Edição inline (prioridade, recorrência, prazo)
  const onEdit = async (id, patch) => {
    try {
      await updateTodo(id, patch)
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const onToggle = async (todo) => {
    try {
      await updateTodo(todo.id, { done: !todo.done })
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const onDelete = async (id) => {
    try {
      await deleteTodo(id)
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const onClearDone = async () => {
    try {
      for (const td of todos.filter((x) => x.done)) await deleteTodo(td.id)
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const sorted = [...todos].sort((a, b) => {
    if (a.done !== b.done) return a.done ? 1 : -1
    return (a.sortOrder ?? 0) - (b.sortOrder ?? 0)
  })
  const doneCount = todos.filter((x) => x.done).length
  const now = Date.now()

  return (
    <div>
      <h1 className="page-title">{t('TODOs')}</h1>
      <p className="subtitle">{t('Lista rápida de pendências.')}</p>

      {error && <div className="banner">{error}</div>}

      <div className="toolbar" style={{ flexWrap: 'wrap' }}>
        <input
          placeholder={t('Nova pendência')}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onAdd()}
        />
        <select value={priority} onChange={(e) => setPriority(e.target.value)}>
          {PRIORITIES.map(([v, l]) => (
            <option key={v} value={v}>
              {t(l)}
            </option>
          ))}
        </select>
        <select value={recurrence} onChange={(e) => setRecurrence(e.target.value)}>
          {RECURRENCES.map(([v, l]) => (
            <option key={v} value={v}>
              {v !== 'NONE' ? '🔁 ' : ''}{t(l)}
            </option>
          ))}
        </select>
        <input
          type="datetime-local"
          title={t('Agendar (opcional)')}
          value={dueAt}
          onChange={(e) => setDueAt(e.target.value)}
        />
        <button onClick={onAdd}>{t('Adicionar')}</button>
      </div>

      <div className="card">
        {sorted.map((td) => {
          const overdue = !td.done && td.dueAt && new Date(td.dueAt).getTime() <= now
          return (
            <div key={td.id} className="row" style={{ flexWrap: 'wrap', gap: 6 }}>
              <input type="checkbox" checked={!!td.done} onChange={() => onToggle(td)} />
              <span
                style={{ flex: 1, minWidth: 160, textDecoration: td.done ? 'line-through' : 'none' }}
                className={td.done ? 'muted' : undefined}
              >
                {td.recurrence && td.recurrence !== 'NONE' ? '🔁 ' : ''}
                {td.text}
              </span>
              <select
                style={{ fontSize: 11 }}
                value={td.priority || 'MEDIUM'}
                onChange={(e) => onEdit(td.id, { priority: e.target.value })}
                title={t('Prioridade')}
              >
                {PRIORITIES.map(([v, l]) => (
                  <option key={v} value={v}>
                    {t(l)}
                  </option>
                ))}
              </select>
              <select
                style={{ fontSize: 11 }}
                value={td.recurrence || 'NONE'}
                onChange={(e) => onEdit(td.id, { recurrence: e.target.value })}
                title={t('Recorrência')}
              >
                {RECURRENCES.map(([v, l]) => (
                  <option key={v} value={v}>
                    {v !== 'NONE' ? '🔁 ' : ''}{t(l)}
                  </option>
                ))}
              </select>
              <input
                type="datetime-local"
                style={{
                  fontSize: 11,
                  color: overdue ? 'var(--danger, #e5484d)' : undefined,
                  fontWeight: overdue ? 700 : 400,
                }}
                value={toLocalInput(td.dueAt)}
                onChange={(e) => onEdit(td.id, { dueAt: e.target.value || null })}
                title={overdue ? t('Vencido') : t('Agendar (opcional)')}
              />
              {td.dueAt && (
                <button
                  className="ghost"
                  onClick={() => onEdit(td.id, { dueAt: null })}
                  title={t('Remover agendamento')}
                >
                  🚫
                </button>
              )}
              <button className="ghost" onClick={() => onDelete(td.id)}>
                ✕
              </button>
            </div>
          )
        })}
        {todos.length === 0 && <div className="muted">{t('Nenhuma pendência ainda.')}</div>}
      </div>

      <div className="toolbar">
        <span className="muted">
          {tf('{done} de {total} concluídos', { done: doneCount, total: todos.length })}
        </span>
        <button className="ghost" onClick={onClearDone} disabled={doneCount === 0}>
          {t('Limpar concluídos')}
        </button>
      </div>
    </div>
  )
}
