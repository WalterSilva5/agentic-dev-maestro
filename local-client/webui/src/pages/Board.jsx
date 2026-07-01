import { useEffect, useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  getBoard,
  createTask,
  moveTask,
  updateTask,
  getSprints,
  archiveTask,
  unarchiveTask,
  getArchived,
} from '../api'
import TaskDetail from '../components/TaskDetail.jsx'
import SprintPlanning from './SprintPlanning.jsx'
import { t, tf } from '../i18n'

const SPRINT_STATUS_LABELS = {
  PLANEJADA: 'Planejada',
  ATIVA: 'Ativa',
  CONCLUIDA: 'Concluída',
}

export default function Board() {
  const { projectId } = useParams()
  const [board, setBoard] = useState(null)
  const [error, setError] = useState('')
  const [newTitles, setNewTitles] = useState({})
  const [openCode, setOpenCode] = useState(null)

  // Abas: board de fluxo | planejamento de sprints
  const [view, setView] = useState('board') // 'board' | 'planning'

  // Sprints
  const [sprints, setSprints] = useState([])
  const [sprintFilter, setSprintFilter] = useState('all') // 'all' | 'backlog' | <id>
  const defaultedRef = useRef(false) // já aplicou o default (sprint ativa) para este projeto?

  // Arquivados
  const [archived, setArchived] = useState([])
  const [showArchived, setShowArchived] = useState(false)

  const filterParam = sprintFilter === 'all' ? null : sprintFilter

  const load = () =>
    getBoard(projectId, filterParam)
      .then(setBoard)
      .catch((e) => setError(String(e.message || e)))

  const loadSprints = () =>
    getSprints(projectId)
      .then((sp) => {
        setSprints(sp)
        // Ao abrir o projeto, o board mostra a sprint ativa por padrão.
        if (!defaultedRef.current) {
          defaultedRef.current = true
          const active = sp.find((s) => s.status === 'ATIVA')
          if (active) setSprintFilter(String(active.id))
        }
      })
      .catch((e) => setError(e.response?.data?.detail || String(e.message || e)))

  const loadArchived = () =>
    getArchived(projectId)
      .then(setArchived)
      .catch((e) => setError(e.response?.data?.detail || String(e.message || e)))

  useEffect(() => {
    // Novo projeto: re-aplica o default (sprint ativa) e volta pra aba Board.
    defaultedRef.current = false
    setSprintFilter('all')
    setView('board')
  }, [projectId])

  useEffect(() => {
    load()
    loadSprints()
    loadArchived()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, sprintFilter])

  const addTask = async (columnId) => {
    const title = (newTitles[columnId] || '').trim()
    if (!title) return
    const body = { projectId: Number(projectId), columnId, title, type: 'FEATURE', priority: 'MEDIUM' }
    // Cria já dentro da sprint selecionada (se for uma sprint específica)
    if (sprintFilter !== 'all' && sprintFilter !== 'backlog') body.sprintId = Number(sprintFilter)
    try {
      await createTask(body)
      setNewTitles({ ...newTitles, [columnId]: '' })
      load()
      loadSprints()
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
      loadSprints()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const onArchive = async (task) => {
    try {
      await archiveTask(task.code)
      load()
      loadArchived()
      loadSprints()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const onUnarchive = async (task) => {
    try {
      await unarchiveTask(task.code)
      load()
      loadArchived()
      loadSprints()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const assignSprint = async (task, value) => {
    try {
      await updateTask(task.code, { sprintId: value === '' ? null : Number(value) })
      load()
      loadSprints()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  if (error) return <div className="banner">{error}</div>
  if (!board) return <div className="muted">{t('Carregando...')}</div>

  const cols = [...board.columns].sort((a, b) => a.order - b.order)
  const activeSprint = sprints.find((s) => s.status === 'ATIVA')

  return (
    <div>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h1 className="page-title">
          {board.key} · {board.name}
        </h1>
        <Link to="/projects"><button className="ghost">{t('← Projetos')}</button></Link>
      </div>
      <p className="subtitle">{tf('Board kanban via API ({count} colunas).', { count: cols.length })}</p>

      {/* Abas: board de fluxo | planejamento de sprints */}
      <div className="row" style={{ gap: 6, marginBottom: 10 }}>
        <button className={view === 'board' ? '' : 'ghost'} onClick={() => setView('board')}>
          {t('Board')}
        </button>
        <button className={view === 'planning' ? '' : 'ghost'} onClick={() => setView('planning')}>
          {t('Planejamento de Sprints')}
        </button>
      </div>

      {view === 'planning' ? (
        <SprintPlanning
          projectId={projectId}
          onChanged={() => {
            load()
            loadSprints()
          }}
        />
      ) : (
        <>
      {/* Barra de sprints */}
      <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 10 }}>
        <span className="muted">{t('Sprint:')}</span>
        <select value={sprintFilter} onChange={(e) => setSprintFilter(e.target.value)}>
          <option value="all">{t('Todas')}</option>
          <option value="backlog">{t('Backlog')}</option>
          {sprints.map((sp) => (
            <option key={sp.id} value={sp.id}>
              {sp.name} · {t(SPRINT_STATUS_LABELS[sp.status] || sp.status)} ({sp.doneCount}/{sp.taskCount})
            </option>
          ))}
        </select>
        {activeSprint && sprintFilter === 'all' && (
          <button className="ghost" onClick={() => setSprintFilter(String(activeSprint.id))}>
            {tf('Ver sprint ativa: {name}', { name: activeSprint.name })}
          </button>
        )}
        <button className="ghost" onClick={() => setShowArchived((v) => !v)}>
          {showArchived ? t('← Voltar ao board') : tf('Arquivados ({count})', { count: archived.length })}
        </button>
      </div>

      {showArchived && (
        <div className="card">
          <strong>{t('Tarefas arquivadas')}</strong>
          <div className="muted" style={{ margin: '4px 0 8px' }}>
            {t('Cards concluídos há mais de 3 dias são arquivados automaticamente e somem do board.')}
          </div>
          {archived.length === 0 && <div className="muted">{t('Nenhuma tarefa arquivada.')}</div>}
          {archived.map((task) => (
            <div key={task.id} className="row" style={{ alignItems: 'center' }}>
              <div onClick={() => setOpenCode(task.code)} style={{ cursor: 'pointer' }}>
                <span className="code">{task.code}</span> {task.title}{' '}
                <span className="badge-type">{task.type}</span>{' '}
                <span className={`badge-prio ${task.priority}`}>{task.priority}</span>
              </div>
              <button className="ghost" onClick={() => onUnarchive(task)}>
                {t('Desarquivar')}
              </button>
            </div>
          ))}
        </div>
      )}

      {!showArchived && (
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
                <div className="row" style={{ marginTop: 6 }} onClick={(e) => e.stopPropagation()}>
                  <select
                    style={{ fontSize: 11, flex: 1 }}
                    value={task.sprintId ?? ''}
                    onChange={(e) => assignSprint(task, e.target.value)}
                    title={t('Sprint da tarefa')}
                  >
                    <option value="">{t('Backlog')}</option>
                    {sprints.map((sp) => (
                      <option key={sp.id} value={sp.id}>
                        {sp.name}
                      </option>
                    ))}
                  </select>
                </div>
                {!col.isDone && (
                  <div>
                    <button
                      className="ghost move"
                      onClick={(e) => {
                        e.stopPropagation()
                        advance(task, cols)
                      }}
                    >
                      {t('Mover →')}
                    </button>
                  </div>
                )}
                {col.isDone && (
                  <div>
                    <button
                      className="ghost move"
                      onClick={(e) => {
                        e.stopPropagation()
                        onArchive(task)
                      }}
                    >
                      {t('Arquivar')}
                    </button>
                  </div>
                )}
              </div>
            ))}
            <div className="row" style={{ marginTop: 6 }}>
              <input
                placeholder={t('Nova tarefa...')}
                style={{ flex: 1, fontSize: 12 }}
                value={newTitles[col.id] || ''}
                onChange={(e) => setNewTitles({ ...newTitles, [col.id]: e.target.value })}
                onKeyDown={(e) => e.key === 'Enter' && addTask(col.id)}
              />
            </div>
          </div>
        ))}
      </div>
      )}
        </>
      )}

      {openCode && (
        <TaskDetail
          code={openCode}
          onClose={() => setOpenCode(null)}
          onChanged={() => {
            load()
            loadSprints()
          }}
        />
      )}
    </div>
  )
}
