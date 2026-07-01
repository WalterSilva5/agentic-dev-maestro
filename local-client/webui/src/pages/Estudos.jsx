import { useEffect, useState } from 'react'
import { getStudyPlans, createStudyPlan, getTopics, addTopic, updateTopic } from '../api'
import { t } from '../i18n'

const CATEGORIES = ['LINGUAGEM', 'FRAMEWORK', 'CERTIFICACAO', 'CONCEITO', 'CURSO', 'LIVRO']
const STATUSES = ['PENDENTE', 'ESTUDANDO', 'REVISAO', 'CONCLUIDO', 'PULADO']

// Rótulos-fonte em PT; t() é aplicado no uso (no render, após o idioma carregar).
const CATEGORY_LABELS = {
  LINGUAGEM: 'Linguagem',
  FRAMEWORK: 'Framework',
  CERTIFICACAO: 'Certificação',
  CONCEITO: 'Conceito',
  CURSO: 'Curso',
  LIVRO: 'Livro',
}
const STATUS_LABELS = {
  PENDENTE: 'Pendente',
  ESTUDANDO: 'Estudando',
  REVISAO: 'Revisão',
  CONCLUIDO: 'Concluído',
  PULADO: 'Pulado',
}

export default function Estudos() {
  const [plans, setPlans] = useState([])
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState(CATEGORIES[0])
  const [error, setError] = useState('')

  const [expandedId, setExpandedId] = useState(null)
  const [topics, setTopics] = useState([])
  const [topicTitle, setTopicTitle] = useState('')

  const load = () =>
    getStudyPlans()
      .then(setPlans)
      .catch((e) => setError(String(e.message || e)))

  useEffect(() => {
    load()
  }, [])

  const loadTopics = (planId) =>
    getTopics(planId)
      .then(setTopics)
      .catch((e) => setError(e.response?.data?.detail || String(e.message || e)))

  const onCreatePlan = async () => {
    if (!title.trim()) return
    try {
      await createStudyPlan({ title: title.trim(), category })
      setTitle('')
      setCategory(CATEGORIES[0])
      setError('')
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const onToggle = (planId) => {
    if (expandedId === planId) {
      setExpandedId(null)
      setTopics([])
      return
    }
    setExpandedId(planId)
    setTopics([])
    loadTopics(planId)
  }

  const onAddTopic = async (planId) => {
    if (!topicTitle.trim()) return
    try {
      await addTopic(planId, { title: topicTitle.trim(), weight: 1 })
      setTopicTitle('')
      setError('')
      loadTopics(planId)
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const onChangeStatus = async (topicId, status, planId) => {
    try {
      await updateTopic(topicId, { status })
      setError('')
      loadTopics(planId)
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  return (
    <div>
      <h1 className="page-title">{t("Estudos")}</h1>
      <p className="subtitle">{t("Planos de estudo e acompanhamento de tópicos.")}</p>

      {error && <div className="banner">{error}</div>}

      <div className="toolbar">
        <input
          placeholder={t("Título do plano")}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {t(CATEGORY_LABELS[c] || c)}
            </option>
          ))}
        </select>
        <button onClick={onCreatePlan}>{t("+ Criar plano")}</button>
      </div>

      {plans.map((p) => (
        <div key={p.id} className="card">
          <div className="row" onClick={() => onToggle(p.id)} style={{ cursor: 'pointer' }}>
            <div>
              <strong>{p.title}</strong>
              <span className="muted"> · {t(CATEGORY_LABELS[p.category] || p.category)}</span>
            </div>
            <span className="muted">
              {p.doneTopics}/{p.totalTopics}
            </span>
          </div>

          <div
            style={{
              background: 'var(--border)',
              borderRadius: 4,
              height: 8,
              marginTop: 8,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                background: 'var(--accent)',
                height: '100%',
                width: `${p.progress}%`,
              }}
            />
          </div>
          <div className="muted" style={{ marginTop: 4 }}>
            {p.progress}% · {t(STATUS_LABELS[p.status] || p.status)}
          </div>

          {expandedId === p.id && (
            <div style={{ marginTop: 12 }}>
              {topics.map((tp) => (
                <div key={tp.id} className="row">
                  <span>{tp.title}</span>
                  <span className="row" style={{ gap: 8 }}>
                    <select
                      value={tp.status}
                      onChange={(e) => onChangeStatus(tp.id, e.target.value, p.id)}
                    >
                      {STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {t(STATUS_LABELS[s] || s)}
                        </option>
                      ))}
                    </select>
                    <span className="muted">
                      {tp.loggedHours}h / {tp.estimateHours}h
                    </span>
                  </span>
                </div>
              ))}
              {topics.length === 0 && <div className="muted">{t("Nenhum tópico ainda.")}</div>}

              <div className="toolbar" style={{ marginTop: 8 }}>
                <input
                  placeholder={t("Novo tópico")}
                  value={topicTitle}
                  onChange={(e) => setTopicTitle(e.target.value)}
                />
                <button className="ghost" onClick={() => onAddTopic(p.id)}>
                  {t("+ Adicionar tópico")}
                </button>
              </div>
            </div>
          )}
        </div>
      ))}
      {plans.length === 0 && <div className="muted">{t("Nenhum plano de estudo ainda.")}</div>}
    </div>
  )
}
