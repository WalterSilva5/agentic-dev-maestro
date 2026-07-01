import { useEffect, useState } from 'react'
import {
  getStudyPlans,
  createStudyPlan,
  getTopics,
  addTopic,
  updateTopic,
  studyAssistant,
} from '../api'
import { t } from '../i18n'

const TEXT_ACTIONS = ['explain', 'exercises', 'quiz', 'flashcards']

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

  // Assistente de estudo (aplica-se ao plano expandido)
  const [assistTopic, setAssistTopic] = useState('')
  const [assistBusy, setAssistBusy] = useState(false)
  const [assistOutput, setAssistOutput] = useState('')
  const [assistSuggested, setAssistSuggested] = useState([])
  const [assistAsk, setAssistAsk] = useState('')

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

  const resetAssist = () => {
    setAssistTopic('')
    setAssistOutput('')
    setAssistSuggested([])
    setAssistAsk('')
    setAssistBusy(false)
  }

  const onToggle = (planId) => {
    resetAssist()
    if (expandedId === planId) {
      setExpandedId(null)
      setTopics([])
      return
    }
    setExpandedId(planId)
    setTopics([])
    loadTopics(planId)
  }

  const runAssist = async (action, plan) => {
    if (assistBusy) return
    if (TEXT_ACTIONS.includes(action) && !assistTopic) {
      setAssistOutput(t('Selecione um tópico específico para esta ação.'))
      return
    }
    if (action === 'ask' && !assistAsk.trim()) return
    setAssistBusy(true)
    setAssistSuggested([])
    setAssistOutput('')
    try {
      const { result } = await studyAssistant({
        action,
        topic: assistTopic,
        plan: plan.title,
        question: assistAsk.trim(),
        existing: topics.map((tp) => tp.title),
      })
      if (action === 'suggest_topics') setAssistSuggested(result || [])
      else setAssistOutput(result || '')
    } catch (e) {
      setAssistOutput(e.response?.data?.detail || String(e.message || e))
    } finally {
      setAssistBusy(false)
    }
  }

  const addSuggested = async (plan) => {
    const have = new Set(topics.map((tp) => (tp.title || '').trim().toLowerCase()))
    let added = 0
    for (const tp of assistSuggested) {
      const title = (tp.title || '').trim()
      if (!title || have.has(title.toLowerCase())) continue
      try {
        await addTopic(plan.id, { title, weight: 1, estimateHours: tp.estimate_hours || null })
        have.add(title.toLowerCase())
        added += 1
      } catch {
        /* segue com os demais */
      }
    }
    setAssistSuggested([])
    setAssistOutput(t('{n} tópico(s) adicionado(s) ao plano.').replace('{n}', added))
    loadTopics(plan.id)
    load()
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

              {/* Assistente de estudo (sob demanda) */}
              <div
                style={{
                  marginTop: 14,
                  paddingTop: 12,
                  borderTop: '1px solid var(--border)',
                }}
              >
                <strong>{t("Assistente de estudo")}</strong>
                <div className="muted" style={{ margin: '4px 0 8px' }}>
                  {t("Escolha um tópico e clique numa ação. A IA gera sob demanda.")}
                </div>

                <div className="toolbar" style={{ flexWrap: 'wrap' }}>
                  <select value={assistTopic} onChange={(e) => setAssistTopic(e.target.value)}>
                    <option value="">{t("— Plano inteiro —")}</option>
                    {topics.map((tp) => (
                      <option key={tp.id} value={tp.title}>
                        {tp.title}
                      </option>
                    ))}
                  </select>
                  <button disabled={assistBusy} onClick={() => runAssist('explain', p)}>
                    {t("Explicar")}
                  </button>
                  <button disabled={assistBusy} onClick={() => runAssist('exercises', p)}>
                    {t("Exercícios")}
                  </button>
                  <button disabled={assistBusy} onClick={() => runAssist('quiz', p)}>
                    {t("Quiz")}
                  </button>
                  <button disabled={assistBusy} onClick={() => runAssist('flashcards', p)}>
                    {t("Flashcards")}
                  </button>
                  <button
                    className="ghost"
                    disabled={assistBusy}
                    onClick={() => runAssist('suggest_topics', p)}
                  >
                    {t("Sugerir tópicos")}
                  </button>
                </div>

                <div className="toolbar" style={{ marginTop: 8 }}>
                  <input
                    placeholder={t("Tirar dúvida sobre o tópico...")}
                    value={assistAsk}
                    onChange={(e) => setAssistAsk(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && runAssist('ask', p)}
                  />
                  <button className="ghost" disabled={assistBusy} onClick={() => runAssist('ask', p)}>
                    {t("Perguntar")}
                  </button>
                </div>

                {assistBusy && <div className="muted" style={{ marginTop: 8 }}>{t("Pensando...")}</div>}

                {assistSuggested.length > 0 && (
                  <div className="card" style={{ marginTop: 8 }}>
                    <div style={{ marginBottom: 6 }}>
                      <strong>{t("Tópicos sugeridos")}</strong>
                    </div>
                    {assistSuggested.map((tp, i) => (
                      <div key={i} className="row">
                        <span>{tp.title}</span>
                        {tp.estimate_hours ? (
                          <span className="muted">~{tp.estimate_hours}h</span>
                        ) : null}
                      </div>
                    ))}
                    <button style={{ marginTop: 8 }} onClick={() => addSuggested(p)}>
                      {t("+ Adicionar ao plano")}
                    </button>
                  </div>
                )}

                {assistOutput && !assistBusy && (
                  <div
                    className="card"
                    style={{ marginTop: 8, whiteSpace: 'pre-wrap', lineHeight: 1.5 }}
                  >
                    {assistOutput}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      ))}
      {plans.length === 0 && <div className="muted">{t("Nenhum plano de estudo ainda.")}</div>}
    </div>
  )
}
