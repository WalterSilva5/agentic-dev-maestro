import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getBoard, createTask, moveTask } from '../api'
import TaskDetail from '../components/TaskDetail.jsx'

export default function Board() {
  const { projectId } = useParams()
  const [board, setBoard] = useState(null)
  const [error, setError] = useState('')
  const [newTitles, setNewTitles] = useState({})
  const [openCode, setOpenCode] = useState(null)

  const load = () =>
    getBoard(projectId)
      .then(setBoard)
      .catch((e) => setError(String(e.message || e)))

  useEffect(() => {
    load()
  }, [projectId])

  const addTask = async (columnId) => {
    const title = (newTitles[columnId] || '').trim()
    if (!title) return
    try {
      await createTask({ projectId: Number(projectId), columnId, title, type: 'FEATURE', priority: 'MEDIUM' })
      setNewTitles({ ...newTitles, [columnId]: '' })
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const advance = async (task, columns) => {
    const idx = columns.findIndex((c) => c.id === task.columnId)
    const next = columns[idx + 1]
    if (!next) return
    try {
      await moveTask(task.code, next.id)
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  if (error) return <div className="banner">{error}</div>
  if (!board) return <div className="muted">Carregando...</div>

  const cols = [...board.columns].sort((a, b) => a.order - b.order)

  return (
    <div>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h1 className="page-title">
          {board.key} · {board.name}
        </h1>
        <Link to="/projects"><button className="ghost">← Projetos</button></Link>
      </div>
      <p className="subtitle">Board kanban via API ({cols.length} colunas).</p>

      <div className="board">
        {cols.map((col) => (
          <div key={col.id} className="column">
            <h3>
              <span>{col.name}</span>
              <span className="count">{col.tasks.length}</span>
            </h3>
            {col.tasks.map((task) => (
              <div key={task.id} className="task" onClick={() => setOpenCode(task.code)}>
                <div className="code">{task.code}</div>
                <div className="ttitle">{task.title}</div>
                <span className="badge-type">{task.type}</span>
                <span className={`badge-prio ${task.priority}`}>{task.priority}</span>
                {!col.isDone && (
                  <div>
                    <button
                      className="ghost move"
                      onClick={(e) => {
                        e.stopPropagation()
                        advance(task, cols)
                      }}
                    >
                      Mover →
                    </button>
                  </div>
                )}
              </div>
            ))}
            <div className="row" style={{ marginTop: 6 }}>
              <input
                placeholder="Nova tarefa..."
                style={{ flex: 1, fontSize: 12 }}
                value={newTitles[col.id] || ''}
                onChange={(e) => setNewTitles({ ...newTitles, [col.id]: e.target.value })}
                onKeyDown={(e) => e.key === 'Enter' && addTask(col.id)}
              />
            </div>
          </div>
        ))}
      </div>

      {openCode && (
        <TaskDetail
          code={openCode}
          onClose={() => setOpenCode(null)}
          onChanged={load}
        />
      )}
    </div>
  )
}
