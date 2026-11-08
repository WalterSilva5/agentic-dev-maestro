import { useEffect, useMemo, useState } from 'react'
import Swal from 'sweetalert2'
import {
  getWorkspaces, getProjects, getTeamWeekly, saveTeamNote, teamReportUrl,
} from '../api'
import { getActiveProjectId } from '../components/ProjectSelector.jsx'
import { t, tf } from '../i18n'

const iso = (d) => d.toISOString().slice(0, 10)
const hoje = () => iso(new Date())
const somarDias = (dataIso, dias) => {
  const d = new Date(`${dataIso}T12:00:00`)
  d.setDate(d.getDate() + dias)
  return iso(d)
}

const VAZIO = { highlights: '', service: '', attention: '', nextStep: '' }

export default function Time() {
  const [projeto, setProjeto] = useState(null)
  const [semana, setSemana] = useState(hoje())
  const [dados, setDados] = useState(null)
  const [notas, setNotas] = useState({})
  const [salvando, setSalvando] = useState('')
  const [erro, setErro] = useState('')
  const [previa, setPrevia] = useState('')
  const [anonimo, setAnonimo] = useState(false)
  const [carregando, setCarregando] = useState(false)

  // projeto atual vem do seletor do menu (mesma chave do localStorage)
  useEffect(() => {
    ;(async () => {
      try {
        const d = await getWorkspaces()
        const pid = getActiveProjectId(d.active)
        const projetos = await getProjects()
        const achado = projetos.find((p) => String(p.id) === String(pid)) || projetos[0] || null
        setProjeto(achado)
      } catch (e) {
        setErro(String(e.message || e))
      }
    })()
  }, [])

  const carregar = async () => {
    if (!projeto) return
    setCarregando(true)
    try {
      const d = await getTeamWeekly(projeto.id, semana)
      setDados(d)
      const mapa = {}
      for (const m of d.members) mapa[m.name] = { ...VAZIO, ...m.note }
      setNotas(mapa)
      setErro('')
    } catch (e) {
      setErro(e?.response?.data?.detail || String(e.message || e))
    } finally {
      setCarregando(false)
    }
  }

  useEffect(() => {
    carregar() // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projeto?.id, semana])

  const alterar = (membro, campo, valor) =>
    setNotas((n) => ({ ...n, [membro]: { ...(n[membro] || VAZIO), [campo]: valor } }))

  const salvar = async (membro) => {
    setSalvando(membro)
    try {
      await saveTeamNote(projeto.id, {
        member: membro,
        weekStart: dados.week.start,
        ...(notas[membro] || VAZIO),
      })
      setDados((d) => ({
        ...d,
        members: d.members.map((m) => (m.name === membro ? { ...m, note: { ...notas[membro] } } : m)),
        notesPending: Math.max(0, (d.notesPending || 0) - 1),
      }))
      setPrevia('')
    } catch (e) {
      Swal.fire({
        icon: 'error',
        title: t('Falha ao salvar'),
        text: typeof e?.response?.data?.detail === 'string' ? e.response.data.detail : String(e.message || e),
      })
    } finally {
      setSalvando('')
    }
  }

  const verPrevia = async (anon = anonimo) => {
    if (!dados) return
    try {
      const r = await fetch(teamReportUrl(projeto.id, dados.week.start, anon))
      setPrevia(await r.text())
    } catch (e) {
      setErro(String(e.message || e))
    }
  }

  const baixar = (anon = false) => {
    if (!dados) return
    window.open(teamReportUrl(projeto.id, dados.week.start, anon), '_blank')
  }

  const copiar = async () => {
    try {
      const r = await fetch(teamReportUrl(projeto.id, dados.week.start, anonimo))
      await navigator.clipboard.writeText(await r.text())
      Swal.fire({ icon: 'success', title: t('Relatório copiado'), timer: 1400, showConfirmButton: false })
    } catch {
      setErro(t('Não foi possível copiar.'))
    }
  }

  const resumo = dados?.summary
  const semNota = useMemo(
    () => (dados?.members || []).filter((m) => !Object.values(notas[m.name] || {}).some(Boolean)).length,
    [dados, notas],
  )

  if (!projeto && !erro) {
    return (
      <div>
        <h1 className="page-title">{t('Time')}</h1>
        <p className="subtitle">{t('Carregando projeto…')}</p>
      </div>
    )
  }

  if (!projeto) {
    return (
      <div>
        <h1 className="page-title">{t('Time')}</h1>
        {erro && <div className="banner">{erro}</div>}
        <div className="card">{t('Escolha um projeto no menu lateral para acompanhar o time.')}</div>
      </div>
    )
  }

  return (
    <div>
      <div className="row" style={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
        <div>
          <h1 className="page-title" style={{ marginBottom: 2 }}>{t('Time')}</h1>
          <p className="subtitle" style={{ margin: 0 }}>
            {projeto.key} · {projeto.name} — {t('report semanal por membro, a partir do board + suas anotações')}
          </p>
        </div>
        <div className="row" style={{ gap: 6, alignItems: 'center' }}>
          <button className="ghost" onClick={() => setSemana(somarDias(dados?.week?.start || semana, -7))} title={t('Semana anterior')}>‹</button>
          <strong style={{ minWidth: 150, textAlign: 'center' }}>
            {dados ? dados.week.label : '—'}
          </strong>
          <button className="ghost" onClick={() => setSemana(somarDias(dados?.week?.start || semana, 7))} title={t('Semana seguinte')}>›</button>
          <button className="ghost" onClick={() => setSemana(hoje())}>{t('Hoje')}</button>
        </div>
      </div>

      {erro && <div className="banner">{erro}</div>}
      {carregando && <p className="muted">{t('Carregando…')}</p>}

      {resumo && (
        <div className="card" style={{ marginTop: 12 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12 }}>
            {[
              [t('Progresso do board'), `${resumo.done}/${resumo.cards}`, `${resumo.pct}%`],
              [t('Concluídos no período'), resumo.doneInWeek, ''],
              [t('Em aberto'), resumo.open, tf('{n} atrasado(s)', { n: resumo.overdue })],
              [t('Sem responsável'), resumo.unassigned, ''],
            ].map(([rotulo, valor, extra]) => (
              <div key={rotulo}>
                <div className="muted" style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: .6 }}>{rotulo}</div>
                <div style={{ fontSize: 22, fontWeight: 800 }}>{valor}</div>
                {extra && <div className="muted" style={{ fontSize: 11 }}>{extra}</div>}
              </div>
            ))}
          </div>
          {resumo.byModule?.length > 0 && (
            <div className="muted" style={{ fontSize: 11, marginTop: 8 }}>
              {t('Entregas por módulo no período:')} {resumo.byModule.map((m) => `${m.module} ${m.count}`).join(' · ')}
            </div>
          )}
        </div>
      )}

      {dados && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 12, marginTop: 12 }}>
          {dados.members.map((m) => (
            <div key={m.name} className="card">
              <div className="row" style={{ justifyContent: 'space-between', alignItems: 'baseline' }}>
                <h3 style={{ margin: 0 }}>{m.name}</h3>
                <span className="muted" style={{ fontSize: 11 }}>
                  {tf('{n} entrega(s) no período', { n: m.deliveredCount })} · {tf('{n} em aberto', { n: m.open })}
                </span>
              </div>

              <div style={{ marginTop: 8, fontSize: 12 }}>
                <div className="muted" style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: .6, marginBottom: 3 }}>
                  {t('Entregas')}
                </div>
                {m.delivered.length === 0 ? (
                  <span className="muted">{t('Nenhuma conclusão registrada nesta semana.')}</span>
                ) : (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {m.delivered.map((e) => (
                      <span key={e.code} title={`${e.title}${e.module ? ` · ${e.module}` : ''}`}
                        style={{ background: 'var(--accent-soft)', color: 'var(--accent)', borderRadius: 8, padding: '1px 6px', fontSize: 11, fontWeight: 600 }}>
                        {e.code}{e.module ? ` · ${e.module}` : ''}
                      </span>
                    ))}
                  </div>
                )}

                <div className="muted" style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: .6, margin: '8px 0 3px' }}>
                  {t('Em aberto por coluna')}
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {m.byColumn.length === 0
                    ? <span className="muted">{t('Nada em aberto.')}</span>
                    : m.byColumn.map((c) => (
                      <span key={c.name} style={{ fontSize: 11 }}>
                        <b>{c.count}</b> <span className="muted">{c.name}</span>
                      </span>
                    ))}
                  {m.overdue > 0 && (
                    <span style={{ fontSize: 11, color: 'var(--danger)', fontWeight: 700 }}>
                      · {tf('{n} atrasado(s)', { n: m.overdue })}
                    </span>
                  )}
                  {m.reviews > 0 && (
                    <span className="muted" style={{ fontSize: 11 }}>· {tf('{n} revisão(ões)', { n: m.reviews })}</span>
                  )}
                </div>
              </div>

              <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
                {[
                  ['highlights', t('Como está trabalhando')],
                  ['service', t('Serviço/apoio (reviews, infra, suporte)')],
                  ['attention', t('Pontos de atenção (fatos)')],
                  ['nextStep', t('Próximo passo')],
                ].map(([campo, rotulo]) => (
                  <label key={campo} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                    <span className="muted" style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: .5 }}>{rotulo}</span>
                    <textarea
                      value={(notas[m.name] || VAZIO)[campo] || ''}
                      onChange={(e) => alterar(m.name, campo, e.target.value)}
                      style={{ minHeight: 52, fontSize: 12 }}
                      placeholder={campo === 'attention' ? t('ex.: PR sem revisor por 3 dias') : ''}
                    />
                  </label>
                ))}
                <div className="row" style={{ justifyContent: 'flex-end' }}>
                  <button onClick={() => salvar(m.name)} disabled={salvando === m.name}>
                    {salvando === m.name ? t('Salvando…') : t('Salvar anotação')}
                  </button>
                </div>
              </div>
            </div>
          ))}
          {dados.members.length === 0 && (
            <div className="card">{t('Nenhum membro com cards neste projeto.')}</div>
          )}
        </div>
      )}

      {dados && (
        <div className="card" style={{ marginTop: 12 }}>
          <div className="row" style={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
            <div>
              <h3 style={{ margin: 0 }}>{t('Relatório semanal')}</h3>
              <div className="muted" style={{ fontSize: 11 }}>
                {t('Markdown no formato dos acompanhamentos do vault.')}
                {semNota > 0 && ` · ${tf('{n} membro(s) sem anotação', { n: semNota })}`}
              </div>
            </div>
            <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
              <label className="muted" style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, cursor: 'pointer' }}>
                <input type="checkbox" style={{ width: 'auto' }} checked={anonimo} onChange={(e) => { setAnonimo(e.target.checked); setPrevia('') }} />
                {t('Anonimizado (Pessoa A/B/C)')}
              </label>
              <button className="ghost" onClick={() => verPrevia()}>{t('Pré-visualizar')}</button>
              <button className="ghost" onClick={copiar}>{t('Copiar')}</button>
              <button className="ghost" onClick={() => baixar(anonimo)}>{t('Baixar .md')}</button>
            </div>
          </div>
          {previa && (
            <pre style={{ marginTop: 10, maxHeight: 420, overflow: 'auto', background: 'var(--bg)', border: '1px solid var(--border-light)', borderRadius: 8, padding: 10, fontSize: 11.5, whiteSpace: 'pre-wrap' }}>
              {previa}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}
