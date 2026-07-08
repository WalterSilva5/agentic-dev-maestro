import { useNavigate } from 'react-router-dom'
import { t } from '../i18n'

const ITEMS = [
  ['/estudos', '📚', 'Estudos', 'Planos, tópicos e assistente de estudo'],
  ['/metricas', '◧', 'Métricas', 'Velocity, lead time e cycle time'],
  ['/labels', '◉', 'Labels', 'Organize tarefas com labels coloridas'],
  ['/biblioteca', '📇', 'Biblioteca', 'Snippets, runbooks, triagem, code review, git, tempo'],
  ['/api-tester', '🛰', 'Testador de API', 'Monte, execute e salve requisições HTTP'],
  ['/base', '🧠', 'Base de conhecimento', 'Notas com backlinks e Q&A por IA'],
]

export default function Ferramentas() {
  const nav = useNavigate()
  return (
    <div>
      <h1 className="page-title">{t('Ferramentas')}</h1>
      <p className="subtitle">{t('Funcionalidades extras — clique para abrir.')}</p>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
          gap: 14,
          marginTop: 12,
        }}
      >
        {ITEMS.map(([to, icon, label, desc]) => (
          <div
            key={to}
            className="card"
            style={{ cursor: 'pointer', minHeight: 120 }}
            onClick={() => nav(to)}
          >
            <div style={{ fontSize: 30 }}>{icon}</div>
            <div style={{ fontWeight: 700, fontSize: 15, marginTop: 6 }}>{t(label)}</div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>{t(desc)}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
