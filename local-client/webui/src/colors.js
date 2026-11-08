// Paleta única do Maestro (web) — espelha maestro_local/gui/theme.py.

export const TYPE_COLORS = {
  FEATURE: '#2563EB',
  BUG: '#DC2626',
  TECH_DEBT: '#EA580C',
  IMPROVEMENT: '#16A34A',
  CHORE: '#71717A',
}

export const TYPE_LABELS = {
  FEATURE: 'Feature',
  BUG: 'Bug',
  TECH_DEBT: 'Tech Debt',
  IMPROVEMENT: 'Melhoria',
  CHORE: 'Tarefa',
}

export const PRIORITY_COLORS = {
  LOW: '#71717A',
  MEDIUM: '#2563EB',
  HIGH: '#EA580C',
  URGENT: '#DC2626',
}

export const PRIORITY_LABELS = {
  LOW: 'Baixa',
  MEDIUM: 'Média',
  HIGH: 'Alta',
  URGENT: 'Urgente',
}

// Cor estável por coluna ("baia"): mesma ordem, mesma cor.
export const COLUMN_COLORS = [
  '#4f46e5', '#0891b2', '#f59e0b', '#db2777', '#16a34a', '#7c3aed',
  '#0ea5e9', '#dc2626', '#ca8a04', '#059669', '#9333ea', '#64748b',
]

export const colorForType = (type) => TYPE_COLORS[type] || '#868E96'
export const typeLabel = (type) => TYPE_LABELS[type] || type || 'Tarefa'
export const colorForPriority = (priority) => PRIORITY_COLORS[priority] || '#71717A'
export const colorForColumn = (order, id) => {
  const base = Number.isFinite(order) ? order : 0
  const extra = Number.isFinite(id) ? id : 0
  return COLUMN_COLORS[(base + extra) % COLUMN_COLORS.length]
}
