import { useEffect, useMemo, useState } from 'react'
import Swal from 'sweetalert2'
import {
  getProjectDaily,
  createProjectDaily,
  updateProjectDaily,
  deleteProjectDaily,
  getProjectDailySummary,
  exportProjectDaily,
  importProjectDaily,
} from '../api'
import { t } from '../i18n'

const KINDS = [
  ['WORK', 'Trabalho', '#16a34a'],
  ['BLOCKER', 'Bloqueio', '#dc2626'],
  ['DECISION', 'Decisão', '#4f46e5'],
  ['NOTE', 'Nota', '#6b7280'],
]
const KIND_COLOR = Object.fromEntries(KINDS.map(([k, , c]) => [k, c]))
const KIND_LABEL = Object.fromEntries(KINDS.map(([k, l]) => [k, l]))

function todayISO() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

export default function ProjectDaily({ projectId, author }) {
  const [entries, setEntries] = useState([])
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')

  // formulário
  const [body, setBody] = useState('')
  const [kind, setKind] = useState('WORK')
  const [date, setDate] = useState(todayISO())
  const [minutes, setMinutes] = useState('')
  const [taskCode, setTaskCode] = useState('')

  // filtros
  const [filterFrom, setFilterFrom] = useState('')
  const [filterTo, setFilterTo] = useState('')
  const [filterKind, setFilterKind] = useState('')
  const [filterAuthor, setFilterAuthor] = useState('')
  const [search, setSearch] = useState('')

  const [editing, setEditing] = useState(null)

  const load = () => {
    const params = {}
    if (filterFrom) params.dateFrom = filterFrom
    if (filterTo) params.dateTo = filterTo
    if (filterKind) params.kind = filterKind
    if (filterAuthor.trim()) params.author = filterAuthor.trim()
    if (search.trim()) params.q = search.trim()
    getProjectDaily(projectId, params).then(setEntries).catch((e) => setError(String(e.message || e)))
    getProjectDailySummary(projectId, {
      ...(filterFrom ? { dateFrom: filterFrom } : {}),
      ...(filterTo ? { dateTo: filterTo } : {}),
    }).then(setSummary).catch(() => setSummary(null))
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, [projectId, filterFrom, filterTo, filterKind, filterAuthor, search])

  const submit = async () => {
    if (!body.trim()) return
    try {
      await createProjectDaily(projectId, {
        body: body.trim(),
        date,
        kind,
        author: author || null,
        minutes: minutes ? Number(minutes) : null,
        taskCode: taskCode.trim() || null,
      })
      setBody('')
      setMinutes('')
      setTaskCode('')
      setError('')
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const saveEdit = async () => {
    if (!editing) return
    try {
      await updateProjectDaily(editing.id, {
        body: editing.body,
        date: editing.date,
        kind: editing.kind,
        minutes: editing.minutes === '' || editing.minutes == null ? null : Number(editing.minutes),
        taskCode: editing.taskCode || '',
      })
      setEditing(null)
      load()
    } catch (e) {
      setError(e.response?.data?.detail || String(e.message || e))
    }
  }

  const remove = async (entry) => {
    const r = await Swal.fire({
      title: t('Excluir este registro?'),
      text: `${entry.date} · ${KIND_LABEL[entry.kind] || entry.kind}`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: t('Excluir'),
      cancelButtonText: t('Cancelar'),
    })
    if (!r.isConfirmed) return
    try {
      await deleteProjectDaily(entry.id)
      load()
    } catch (e) {
      setError(String(e.message || e))
    }
  }

  const exportDay = async () => {
    try {
      const data = await exportProjectDaily(projectId, date)
      const blob = new Blob([data.markdown], { type: 'text/markdown;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = data.filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (e) {
      const msg = e.response?.data?.detail || String(e.message || e)
      Swal.fire({ icon: 'info', title: t('Nada para exportar'), text: msg })
    }
  }

  const importDay = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.md,text/markdown,text/plain'
    input.onchange = async () => {
      const file = input.files?.[0]
      if (!file) return
      const content = await file.text()
      const conf = await Swal.fire({
        title: t('Importar daily'),
        html: `<p>${t('Importar')} <b>${file.name}</b>?</p><p class="muted">${t('Os registros do dia serão substituídos.')}</p>`,
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: t('Importar'),
        cancelButtonText: t('Cancelar'),
      })
      if (!conf.isConfirmed) return
      try {
        const r = await importProjectDaily(projectId, { content, replace: true })
        Swal.fire({ icon: 'success', title: t('Importado'), text: `${r.date} · ${r.created} ${t('bloco(s)')}`, timer: 1800, showConfirmButton: false })
        load()
      } catch (e) {
        Swal.fire({ icon: 'error', title: t('Erro'), text: e.response?.data?.detail || String(e.message || e) })
      }
    }
    input.click()
  }

  // agrupa por dia
  const grouped = useMemo(() => {
    const map = new Map()
    for (const e of entries) {
      if (!map.has(e.date)) map.set(e.date, [])
      map.get(e.date).push(e)
    }
    return [...map.entries()].sort((a, b) => (a[0] < b[0] ? 1 : -1))
  }, [entries])

  const hasFilters = !!(filterFrom || filterTo || filterKind || filterAuthor.trim() || search.trim())

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {error && <div className="banner">{error}</div>}

      {summary && (
        <div className="card" style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
          <span className="muted" style={{ fontSize: 11, fontWeight: 700, letterSpacing: .6, textTransform: 'uppercase' }}>
            {t('Resumo')}
          </span>
          <span style={{ fontSize: 13 }}>
            <b>{summary.total}</b> {t('registro(s) em')} <b>{summary.days.length}</b> {t('dia(s)')}
          </span>
          {summary.totalMinutes > 0 && (
            <span style={{ fontSize: 13 }}>
              <b>{Math.round(summary.totalMinutes / 60 * 10) / 10}h</b> {t('registradas')}
            </span>
          )}
          {KINDS.filter(([k]) => summary.byKind?.[k] > 0).map(([k, label, color]) => (
            <span key={k} style={{ fontSize: 12, color, fontWeight: 600 }}>
              {label}: {summary.byKind[k]}
            </span>
          ))}
          {summary.days.slice(0, 6).map((d) => (
            <span key={d.date} className="muted" style={{ fontSize: 11 }}>
              {d.date}: {d.entries}
            </span>
          ))}
          <span style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
            <button className="ghost" style={{ padding: '3px 9px', fontSize: 11 }} onClick={exportDay} title={t('Exportar o dia em markdown (formato do vault)')}>
              ⬇ {t('Exportar .md')}
            </button>
            <button className="ghost" style={{ padding: '3px 9px', fontSize: 11 }} onClick={importDay} title={t('Importar um doc de daily (.md)')}>
              ⬆ {t('Importar .md')}
            </button>
          </span>
        </div>
      )}

      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <strong>{t('Novo registro do dia')}</strong>
        <textarea
          rows={3}
          placeholder={t('O que você fez hoje neste projeto...')}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) submit()
          }}
        />
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} style={{ width: 150 }} />
          <select value={kind} onChange={(e) => setKind(e.target.value)} style={{ width: 130 }}>
            {KINDS.map(([k, label]) => (
              <option key={k} value={k}>{t(label)}</option>
            ))}
          </select>
          <input
            type="number"
            min="0"
            placeholder={t('min')}
            value={minutes}
            onChange={(e) => setMinutes(e.target.value)}
            style={{ width: 90 }}
          />
          <input
            placeholder={t('Card (opcional)')}
            value={taskCode}
            onChange={(e) => setTaskCode(e.target.value)}
            style={{ width: 140 }}
          />
          <button onClick={submit} disabled={!body.trim()}>{t('Registrar')}</button>
          <span className="muted" style={{ fontSize: 11 }}>{t('Ctrl+Enter para salvar')}</span>
        </div>
      </div>

      <div className="card" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          placeholder={t('Buscar no texto...')}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ minWidth: 180, flex: '1 1 180px' }}
        />
        <span className="muted" style={{ fontSize: 11, fontWeight: 700 }}>{t('De')}</span>
        <input type="date" value={filterFrom} onChange={(e) => setFilterFrom(e.target.value)} style={{ width: 150 }} />
        <span className="muted" style={{ fontSize: 11, fontWeight: 700 }}>{t('Até')}</span>
        <input type="date" value={filterTo} onChange={(e) => setFilterTo(e.target.value)} style={{ width: 150 }} />
        <select value={filterKind} onChange={(e) => setFilterKind(e.target.value)} style={{ width: 130 }}>
          <option value="">{t('Todos os tipos')}</option>
          {KINDS.map(([k, label]) => (
            <option key={k} value={k}>{t(label)}</option>
          ))}
        </select>
        <input
          placeholder={t('Autor')}
          value={filterAuthor}
          onChange={(e) => setFilterAuthor(e.target.value)}
          style={{ width: 120 }}
        />
        {hasFilters && (
          <button
            className="ghost"
            onClick={() => { setSearch(''); setFilterFrom(''); setFilterTo(''); setFilterKind(''); setFilterAuthor('') }}
          >
            {t('Limpar')}
          </button>
        )}
        <span className="muted" style={{ fontSize: 11, marginLeft: 'auto' }}>{entries.length} {t('registro(s)')}</span>
      </div>

      {grouped.length === 0 && (
        <div className="muted" style={{ fontSize: 13 }}>
          {hasFilters ? t('Nenhum registro para esses filtros.') : t('Nenhum registro ainda. Escreva o primeiro acima.')}
        </div>
      )}

      {grouped.map(([day, items]) => (
        <div className="card" key={day} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <strong style={{ fontFamily: 'monospace' }}>{day}</strong>
            <span className="muted" style={{ fontSize: 11 }}>{items.length} {t('registro(s)')}</span>
          </div>

          {items.map((entry) => (
            <div
              key={entry.id}
              style={{
                borderLeft: `3px solid ${KIND_COLOR[entry.kind] || '#6b7280'}`,
                paddingLeft: 10,
                display: 'flex',
                flexDirection: 'column',
                gap: 4,
              }}
            >
              {editing && editing.id === entry.id ? (
                <>
                  <textarea rows={3} value={editing.body} onChange={(e) => setEditing({ ...editing, body: e.target.value })} />
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                    <input type="date" value={editing.date} onChange={(e) => setEditing({ ...editing, date: e.target.value })} style={{ width: 150 }} />
                    <select value={editing.kind} onChange={(e) => setEditing({ ...editing, kind: e.target.value })} style={{ width: 130 }}>
                      {KINDS.map(([k, label]) => (
                        <option key={k} value={k}>{t(label)}</option>
                      ))}
                    </select>
                    <input type="number" min="0" placeholder={t('min')} value={editing.minutes ?? ''} onChange={(e) => setEditing({ ...editing, minutes: e.target.value })} style={{ width: 90 }} />
                    <input placeholder={t('Card (opcional)')} value={editing.taskCode || ''} onChange={(e) => setEditing({ ...editing, taskCode: e.target.value })} style={{ width: 130 }} />
                    <button onClick={saveEdit}>{t('Salvar')}</button>
                    <button className="ghost" onClick={() => setEditing(null)}>{t('Cancelar')}</button>
                  </div>
                </>
              ) : (
                <>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 10, fontWeight: 700, color: KIND_COLOR[entry.kind] || '#6b7280', textTransform: 'uppercase' }}>
                      {t(KIND_LABEL[entry.kind] || entry.kind)}
                    </span>
                    {entry.author && <span className="muted" style={{ fontSize: 11 }}>{entry.author}</span>}
                    {entry.minutes ? <span className="muted" style={{ fontSize: 11 }}>{entry.minutes} {t('min')}</span> : null}
                    {entry.taskCode && <span className="badge-type" style={{ fontSize: 10 }}>{entry.taskCode}</span>}
                    <span className="muted" style={{ fontSize: 10, marginLeft: 'auto' }}>
                      {entry.createdAt ? new Date(entry.createdAt).toLocaleTimeString() : ''}
                    </span>
                    <button className="ghost" style={{ padding: '1px 6px', fontSize: 10 }} onClick={() => setEditing({ ...entry })}>{t('Editar')}</button>
                    <button className="ghost" style={{ padding: '1px 6px', fontSize: 10, color: 'var(--danger)' }} onClick={() => remove(entry)}>✕</button>
                  </div>
                  <div style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>{entry.body}</div>
                </>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
