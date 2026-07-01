import { useEffect, useState } from 'react'
import { getTodos, addTodo, updateTodo, deleteTodo } from '../api'

export default function Todos() {
  const [todos, setTodos] = useState([])
  const [text, setText] = useState('')
  const [error, setError] = useState('')

  const load = () =>
    getTodos().then(setTodos).catch((e) => setError(String(e.message || e)))

  useEffect(() => {
    load()
  }, [])

  const onAdd = async () => {
    if (!text.trim()) return
    try {
      await addTodo(text.trim())
      setText('')
      setError('')
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const onToggle = async (todo) => {
    try {
      await updateTodo(todo.id, { done: !todo.done })
      setError('')
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const onDelete = async (id) => {
    try {
      await deleteTodo(id)
      setError('')
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const onClearDone = async () => {
    try {
      const done = todos.filter((t) => t.done)
      for (const t of done) {
        await deleteTodo(t.id)
      }
      setError('')
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const sorted = [...todos].sort((a, b) => {
    if (a.done !== b.done) return a.done ? 1 : -1
    return (a.sortOrder ?? 0) - (b.sortOrder ?? 0)
  })

  const doneCount = todos.filter((t) => t.done).length

  return (
    <div>
      <h1 className="page-title">TODOs</h1>
      <p className="subtitle">Lista rápida de pendências.</p>

      {error && <div className="banner">{error}</div>}

      <div className="toolbar">
        <input
          placeholder="Nova pendência"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') onAdd()
          }}
        />
        <button onClick={onAdd}>Adicionar</button>
      </div>

      <div className="card">
        {sorted.map((t) => (
          <div key={t.id} className="row">
            <input
              type="checkbox"
              checked={!!t.done}
              onChange={() => onToggle(t)}
            />
            <span
              style={{
                flex: 1,
                textDecoration: t.done ? 'line-through' : 'none',
              }}
              className={t.done ? 'muted' : undefined}
            >
              {t.text}
            </span>
            <button className="ghost" onClick={() => onDelete(t.id)}>
              ✕
            </button>
          </div>
        ))}
        {todos.length === 0 && <div className="muted">Nenhuma pendência ainda.</div>}
      </div>

      <div className="toolbar">
        <span className="muted">
          {doneCount} de {todos.length} concluídos
        </span>
        <button
          className="ghost"
          onClick={onClearDone}
          disabled={doneCount === 0}
        >
          Limpar concluídos
        </button>
      </div>
    </div>
  )
}
