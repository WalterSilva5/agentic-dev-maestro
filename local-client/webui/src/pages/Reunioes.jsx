import { useEffect, useMemo, useState } from 'react'
import Swal from 'sweetalert2'
import {
  listRecordings, getRecording, updateRecording, deleteRecording,
  archiveRecording, recordingExportUrl, recordingAudioUrl,
  analyzeRecording, getWorkspaces,
} from '../api.js'
import { getActiveProjectId } from '../components/ProjectSelector.jsx'
import { t, tf } from '../i18n'

// Markdown mínimo (títulos, listas, negrito, código) — sem dependência nova.
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

function mdToHtml(md) {
  const linhas = esc(md || '').split('\n')
  const out = []
  let lista = null
  const fechaLista = () => { if (lista) { out.push(`</${lista}>`); lista = null } }
  for (const bruta of linhas) {
    const linha = bruta.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/`(.+?)`/g, '<code>$1</code>')
    if (!linha.trim()) { fechaLista(); continue }
    const h = linha.match(/^(#{1,4})\s+(.*)$/)
    if (h) { fechaLista(); out.push(`<h${h[1].length + 1}>${h[2]}</h${h[1].length + 1}>`); continue }
    const li = linha.match(/^\s*[-*]\s+(.*)$/)
    if (li) {
      if (lista !== 'ul') { fechaLista(); out.push('<ul>'); lista = 'ul' }
      out.push(`<li>${li[1]}</li>`)
      continue
    }
    const ol = linha.match(/^\s*\d+[.)]\s+(.*)$/)
    if (ol) {
      if (lista !== 'ol') { fechaLista(); out.push('<ol>'); lista = 'ol' }
      out.push(`<li>${ol[1]}</li>`)
      continue
    }
    fechaLista()
    out.push(`<p>${linha}</p>`)
  }
  fechaLista()
  return out.join('\n')
}

const textoErro = (e) => {
  const d = e?.response?.data?.detail ?? e?.message ?? e
  if (typeof d === 'string') return d
  try { return JSON.stringify(d) } catch { return String(d) }
}

const linhas = (txt) => (txt || '').split('\n').map((s) => s.trim()).filter(Boolean)
const dt = (iso) => (iso ? new Date(iso).toLocaleString() : '—')
const dur = (s) => {
  const total = Math.round(s || 0)
  if (!total) return ''
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const sec = total % 60
  return h ? `${h}h ${m}min` : m ? `${m}min ${sec}s` : `${sec}s`
}

export default function Reunioes() {
  const [itens, setItens] = useState([])
  const [q, setQ] = useState('')
  const [kind, setKind] = useState('')
  const [arquivadas, setArquivadas] = useState('hide')
  const [sel, setSel] = useState(null)
  const [detalhe, setDetalhe] = useState(null)
  const [draft, setDraft] = useState(null)
  const [tab, setTab] = useState('resumo')
  const [salvando, setSalvando] = useState(false)
  const [msg, setMsg] = useState('')
  const [erro, setErro] = useState('')
  const [preview, setPreview] = useState(false)
  const [projeto, setProjeto] = useState(null)
  const [analise, setAnalise] = useState(null)
  const [analisando, setAnalisando] = useState(false)

  const carregar = async () => {
    try {
      const dados = await listRecordings({ kind: kind || undefined, archived: arquivadas, q: q || undefined })
      setItens(dados)
      setErro('')
      if (!sel && dados.length) abrir(dados[0].id)
    } catch (e) {
      setErro(textoErro(e))
    }
  }

  const abrir = async (id) => {
    if (!id) return
    try {
      const d = await getRecording(id)
      setSel(id)
      setDetalhe(d)
      setDraft({
        title: d.title || '',
        topic: d.topic || '',
        tags: (d.tags || []).join(', '),
        transcript: d.transcript || '',
        markdown: d.markdown || '',
        plan: (d.sections?.plan || []).join('\n'),
        tips: (d.sections?.tips || []).join('\n'),
        decisions: (d.sections?.decisions || []).join('\n'),
        actions: (d.sections?.actionItems || []).map((a) => ({ ...a })),
        questions: (d.sections?.questions || []).map((x) => ({ ...x })),
      })
      setErro('')
      setMsg('')
    } catch (e) {
      setErro(textoErro(e))
    }
  }

  useEffect(() => { carregar() /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [kind, arquivadas])

  useEffect(() => {
    ;(async () => {
      try {
        const d = await getWorkspaces()
        const pid = getActiveProjectId(d.active)
        if (pid) setProjeto({ id: Number(pid) })
      } catch { /* sem projeto ativo: analisa só a transcrição */ }
    })()
  }, [])

  const analisar = async () => {
    if (!sel) return
    setAnalisando(true)
    try {
      const d = await analyzeRecording(sel, projeto?.id ? { projectId: projeto.id } : {})
      setAnalise(d)
    } catch (e) {
      setErro(textoErro(e))
    } finally {
      setAnalisando(false)
    }
  }

  const salvarAnalise = async () => {
    if (!sel) return
    try {
      const d = await analyzeRecording(sel, { projectId: projeto?.id, save: true })
      setAnalise(d)
      await abrir(sel)
      setMsg(t('Análise salva na reunião.'))
    } catch (e) {
      setErro(textoErro(e))
    }
  }

  const sujo = useMemo(() => {
    if (!detalhe || !draft) return false
    return (
      draft.title !== (detalhe.title || '') ||
      draft.topic !== (detalhe.topic || '') ||
      draft.tags !== (detalhe.tags || []).join(', ') ||
      draft.transcript !== (detalhe.transcript || '') ||
      draft.markdown !== (detalhe.markdown || '')
    )
  }, [draft, detalhe])

  const salvar = async () => {
    if (!sel || !draft) return
    setSalvando(true)
    try {
      const d = await updateRecording(sel, {
        title: draft.title,
        topic: draft.topic,
        tags: draft.tags.split(',').map((s) => s.trim()).filter(Boolean),
        transcript: draft.transcript,
        markdown: draft.markdown,
        liveState: {
          plan: linhas(draft.plan),
          tips: linhas(draft.tips),
          decisions: linhas(draft.decisions),
          action_items: draft.actions
            .filter((a) => (a.description || '').trim())
            .map((a) => ({ description: a.description.trim(), assignee: (a.assignee || '').trim() })),
          questions: draft.questions
            .filter((x) => (x.question || '').trim())
            .map((x) => ({ question: x.question.trim(), answer: (x.answer || '').trim(), resolved: !!x.resolved })),
        },
      })
      setDetalhe(d)
      setMsg(t('Reunião salva.'))
      carregar()
    } catch (e) {
      setErro(textoErro(e))
    } finally {
      setSalvando(false)
    }
  }

  const arquivar = async (valor) => {
    if (!sel) return
    try {
      await archiveRecording(sel, valor)
      setMsg(valor ? t('Reunião arquivada.') : t('Reunião desarquivada.'))
      await carregar()
      await abrir(sel)
    } catch (e) {
      setErro(textoErro(e))
    }
  }

  const excluir = async () => {
    if (!sel) return
    const r = await Swal.fire({
      title: t('Excluir reunião?'),
      text: detalhe?.title || '',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: t('Excluir'),
      cancelButtonText: t('Cancelar'),
    })
    if (!r.isConfirmed) return
    try {
      await deleteRecording(sel)
      setSel(null); setDetalhe(null); setDraft(null)
      setMsg(t('Reunião excluída.'))
      carregar()
    } catch (e) {
      setErro(textoErro(e))
    }
  }

  const exportar = (formato) => {
    if (!sel) return
    window.open(recordingExportUrl(sel, formato), '_blank')
  }

  const copiar = async () => {
    if (!sel) return
    try {
      const resp = await fetch(recordingExportUrl(sel, 'md'))
      const texto = await resp.text()
      await navigator.clipboard.writeText(texto)
      setMsg(t('Markdown copiado.'))
    } catch {
      setErro(t('Não foi possível copiar.'))
    }
  }

  const set = (campo, valor) => setDraft((d) => ({ ...d, [campo]: valor }))
  const setAcao = (i, campo, valor) => setDraft((d) => {
    const actions = d.actions.map((a, j) => (j === i ? { ...a, [campo]: valor } : a))
    return { ...d, actions }
  })
  const setPergunta = (i, campo, valor) => setDraft((d) => {
    const questions = d.questions.map((x, j) => (j === i ? { ...x, [campo]: valor } : x))
    return { ...d, questions }
  })

  const Seletor = (
    <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 10 }}>
      <input placeholder={t('🔍 Buscar por título, tópico ou transcrição...')} value={q}
        onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && carregar()}
        style={{ flex: '1 1 220px' }} />
      <select value={kind} onChange={(e) => setKind(e.target.value)}>
        <option value="">{t('Todos os tipos')}</option>
        <option value="meeting">{t('Reuniões')}</option>
        <option value="study">{t('Estudos')}</option>
      </select>
      <select value={arquivadas} onChange={(e) => setArquivadas(e.target.value)}>
        <option value="hide">{t('Sem arquivadas')}</option>
        <option value="only">{t('Só arquivadas')}</option>
        <option value="all">{t('Todas')}</option>
      </select>
      <button onClick={carregar}>{t('Buscar')}</button>
      <span className="muted" style={{ fontSize: 11 }}>{tf('{n} reunião(ões)', { n: itens.length })}</span>
    </div>
  )

  return (
    <div>
      <h1>{t('Reuniões')}</h1>
      <p className="muted">{t('Gravações do app desktop: o mesmo conteúdo para gerenciar, visualizar, editar e exportar.')}</p>
      {erro && <div className="banner">{erro}</div>}
      {msg && <div className="muted" style={{ marginBottom: 8 }}>{msg}</div>}
      {Seletor}

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(240px, 320px) 1fr', gap: 12, alignItems: 'start' }}>
        {/* lista */}
        <div className="card" style={{ padding: 8, maxHeight: '72vh', overflowY: 'auto' }}>
          {itens.length === 0 && <div className="muted" style={{ padding: 8 }}>{t('Nenhuma reunião encontrada.')}</div>}
          {itens.map((r) => {
            const ativo = r.id === sel
            return (
              <div key={r.id} onClick={() => abrir(r.id)}
                style={{
                  cursor: 'pointer', padding: '8px 10px', borderRadius: 8, marginBottom: 4,
                  border: `1px solid ${ativo ? 'var(--accent)' : 'transparent'}`,
                  background: ativo ? 'var(--accent-soft)' : 'transparent',
                }}>
                <div className="muted" style={{ fontSize: 10 }}>{dt(r.createdAt)}</div>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{r.title || r.topic || t('(sem título)')}</div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 3, fontSize: 10 }}>
                  {r.kind === 'study' && <span className="badge-type">{t('Estudo')}</span>}
                  {r.hasSummary && <span className="badge-type">📝 {t('resumo')}</span>}
                  {r.hasTranscript && <span className="badge-type">💬 {t('transcrição')}</span>}
                  {r.hasAudio && <span className="badge-type">🎧 {t('áudio')}</span>}
                  {r.archivedAt && <span className="badge-type">📦 {t('arquivada')}</span>}
                  {!!r.duration && <span className="muted">{dur(r.duration)}</span>}
                </div>
              </div>
            )
          })}
        </div>

        {/* detalhe */}
        <div className="card" style={{ padding: 14 }}>
          {!detalhe || !draft ? (
            <div className="muted">{t('Selecione uma reunião na lista.')}</div>
          ) : (
            <>
              <div className="row" style={{ gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <input value={draft.title} onChange={(e) => set('title', e.target.value)}
                  placeholder={t('Título da reunião')}
                  style={{ flex: '1 1 260px', fontWeight: 700, fontSize: 15 }} />
                <button onClick={salvar} disabled={salvando}>{salvando ? t('Salvando...') : t('Salvar')}</button>
                {sujo && <span className="muted" style={{ fontSize: 11 }}>● {t('não salvo')}</span>}
              </div>

              <div className="row" style={{ gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                <input value={draft.topic} onChange={(e) => set('topic', e.target.value)}
                  placeholder={t('Tópico')} style={{ flex: '1 1 180px' }} />
                <input value={draft.tags} onChange={(e) => set('tags', e.target.value)}
                  placeholder={t('tags separadas por vírgula')} style={{ flex: '1 1 180px' }} />
              </div>

              <div className="muted" style={{ fontSize: 11, marginTop: 6 }}>
                {dt(detalhe.createdAt)}{detalhe.duration ? ` · ${dur(detalhe.duration)}` : ''}
                {detalhe.language ? ` · ${detalhe.language}` : ''}
              </div>

              <div className="row" style={{ gap: 6, marginTop: 10, flexWrap: 'wrap' }}>
                <button className="ghost" onClick={() => exportar('md')}>⬇ Markdown</button>
                <button className="ghost" onClick={() => exportar('txt')}>⬇ TXT</button>
                <button className="ghost" onClick={() => exportar('json')}>⬇ JSON</button>
                <button className="ghost" onClick={copiar}>{t('Copiar markdown')}</button>
                <span style={{ flex: 1 }} />
                {!detalhe.archivedAt
                  ? <button className="ghost" onClick={() => arquivar(true)}>{t('Arquivar')}</button>
                  : <button className="ghost" onClick={() => arquivar(false)}>{t('Desarquivar')}</button>}
                <button className="ghost" style={{ color: 'var(--danger)' }} onClick={excluir}>{t('Excluir')}</button>
              </div>

              {/* análise com o contexto do projeto (board, atrasos, dailies) */}
              <div className="row" style={{ gap: 8, marginTop: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                <button className="ghost" onClick={analisar} disabled={analisando}>
                  {analisando ? `⏳ ${t('Analisando...')}` : `🧠 ${t('Analisar com contexto')}`}
                </button>
                <span className="muted" style={{ fontSize: 11 }}>
                  {projeto
                    ? t('Usa o board, atrasos e dailies do projeto atual.')
                    : t('Sem projeto ativo: analisa só a transcrição.')}
                </span>
              </div>

              {analise && (
                <div style={{ marginTop: 8, border: '1px solid var(--border-light)', borderRadius: 8, padding: 10, background: 'var(--bg)' }}>
                  <div className="row" style={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 6 }}>
                    <span style={{ fontSize: 11, fontWeight: 700 }}>
                      {analise.engine === 'llm' ? `🧠 ${t('Análise por IA')}` : `📐 ${t('Análise pelo contexto (sem IA)')}`}
                      {analise.usedProjectContext ? ` · ${t('com projeto')}` : ` · ${t('só transcrição')}`}
                    </span>
                    <div className="row" style={{ gap: 6 }}>
                      <button className="ghost" onClick={salvarAnalise}>{t('Salvar na reunião')}</button>
                      <button className="ghost" onClick={() => setAnalise(null)}>{t('Fechar')}</button>
                    </div>
                  </div>

                  {[
                    ['tips', `💡 ${t('Dicas')}`],
                    ['plan', `🗺 ${t('Plano')}`],
                    ['decisions', `📌 ${t('Decisões')}`],
                  ].map(([campo, rotulo]) => (
                    (analise[campo] || []).length > 0 && (
                      <div key={campo} style={{ marginTop: 8 }}>
                        <div className="muted" style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: .5 }}>{rotulo}</div>
                        <ul style={{ margin: '2px 0 0 16px', padding: 0, fontSize: 12 }}>
                          {analise[campo].map((item, i) => <li key={i}>{item}</li>)}
                        </ul>
                      </div>
                    )
                  ))}
                  {(analise.actionItems || []).length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <div className="muted" style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: .5 }}>✅ {t('Ações')}</div>
                      <ul style={{ margin: '2px 0 0 16px', padding: 0, fontSize: 12 }}>
                        {analise.actionItems.map((a, i) => (
                          <li key={i}>{a.description}{a.assignee ? ` — ${a.assignee}` : ''}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {analise.engine === 'heuristic' && (
                    <div className="muted" style={{ fontSize: 10, marginTop: 8 }}>
                      {t('Sem provedor de IA ativo: as dicas vêm só de fatos do board e das dailies.')}
                    </div>
                  )}
                </div>
              )}

              <div className="row" style={{ gap: 4, marginTop: 12, borderBottom: '1px solid var(--border-light)' }}>
                {[
                  ['resumo', t('Resumo')],
                  ['transcricao', t('Transcrição')],
                  ['secoes', t('Seções')],
                  ...(detalhe.hasAudio ? [['audio', t('Áudio')]] : []),
                ].map(([chave, rotulo]) => (
                  <button key={chave} className={tab === chave ? '' : 'ghost'} onClick={() => setTab(chave)}
                    style={{ borderBottomLeftRadius: 0, borderBottomRightRadius: 0 }}>{rotulo}</button>
                ))}
              </div>

              {tab === 'resumo' && (
                <div style={{ marginTop: 10 }}>
                  <div className="row" style={{ gap: 6, marginBottom: 6 }}>
                    <button className="ghost" onClick={() => setPreview((v) => !v)}>
                      {preview ? t('Editar') : t('Pré-visualizar')}
                    </button>
                    <span className="muted" style={{ fontSize: 11 }}>
                      {t('O resumo é o markdown que vai no PDF/exportação.')}
                    </span>
                  </div>
                  {preview ? (
                    <div style={{ background: 'var(--bg)', border: '1px solid var(--border-light)', borderRadius: 8, padding: 12, maxHeight: '48vh', overflowY: 'auto' }}
                      dangerouslySetInnerHTML={{ __html: mdToHtml(draft.markdown || detalhe.markdown) }} />
                  ) : (
                    <textarea value={draft.markdown} onChange={(e) => set('markdown', e.target.value)}
                      placeholder={t('Resumo em markdown (vazio = monta a partir das seções + transcrição na exportação)')}
                      style={{ width: '100%', minHeight: '48vh', fontFamily: 'monospace', fontSize: 12 }} />
                  )}
                </div>
              )}

              {tab === 'transcricao' && (
                <div style={{ marginTop: 10 }}>
                  <div className="muted" style={{ fontSize: 11, marginBottom: 6 }}>
                    {t('Transcrição completa. Editar aqui corrige erros do reconhecimento.')}
                  </div>
                  <textarea value={draft.transcript} onChange={(e) => set('transcript', e.target.value)}
                    style={{ width: '100%', minHeight: '48vh', fontSize: 12 }} />
                </div>
              )}

              {tab === 'secoes' && (
                <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {[['plan', t('🗺 Plano')], ['tips', t('💡 Dicas')], ['decisions', t('📌 Decisões')]].map(([campo, rotulo]) => (
                    <div key={campo}>
                      <div className="muted" style={{ fontSize: 11, fontWeight: 700, marginBottom: 4 }}>{rotulo}</div>
                      <textarea value={draft[campo]} onChange={(e) => set(campo, e.target.value)}
                        placeholder={t('um item por linha')}
                        style={{ width: '100%', minHeight: 70, fontSize: 12 }} />
                    </div>
                  ))}

                  <div>
                    <div className="muted" style={{ fontSize: 11, fontWeight: 700, marginBottom: 4 }}>{t('✅ Ações')}</div>
                    {draft.actions.map((a, i) => (
                      <div key={i} className="row" style={{ gap: 6, marginBottom: 4 }}>
                        <input value={a.description} onChange={(e) => setAcao(i, 'description', e.target.value)}
                          placeholder={t('O que fazer')} style={{ flex: 3 }} />
                        <input value={a.assignee} onChange={(e) => setAcao(i, 'assignee', e.target.value)}
                          placeholder={t('Responsável')} style={{ flex: 1 }} />
                        <button className="ghost" onClick={() => setDraft((d) => ({ ...d, actions: d.actions.filter((_, j) => j !== i) }))}>✕</button>
                      </div>
                    ))}
                    <button className="ghost" onClick={() => setDraft((d) => ({ ...d, actions: [...d.actions, { description: '', assignee: '' }] }))}>
                      + {t('Ação')}
                    </button>
                  </div>

                  <div>
                    <div className="muted" style={{ fontSize: 11, fontWeight: 700, marginBottom: 4 }}>{t('❓ Perguntas')}</div>
                    {draft.questions.map((x, i) => (
                      <div key={i} style={{ border: '1px solid var(--border-light)', borderRadius: 6, padding: 6, marginBottom: 4 }}>
                        <div className="row" style={{ gap: 6 }}>
                          <input value={x.question} onChange={(e) => setPergunta(i, 'question', e.target.value)}
                            placeholder={t('Pergunta')} style={{ flex: 2 }} />
                          <label className="muted" style={{ display: 'flex', gap: 4, alignItems: 'center', fontSize: 11 }}>
                            <input type="checkbox" checked={!!x.resolved} style={{ width: 'auto' }}
                              onChange={(e) => setPergunta(i, 'resolved', e.target.checked)} />
                            {t('resolvida')}
                          </label>
                          <button className="ghost" onClick={() => setDraft((d) => ({ ...d, questions: d.questions.filter((_, j) => j !== i) }))}>✕</button>
                        </div>
                        <input value={x.answer} onChange={(e) => setPergunta(i, 'answer', e.target.value)}
                          placeholder={t('Resposta')} style={{ width: '100%', marginTop: 4 }} />
                      </div>
                    ))}
                    <button className="ghost" onClick={() => setDraft((d) => ({ ...d, questions: [...d.questions, { question: '', answer: '', resolved: false }] }))}>
                      + {t('Pergunta')}
                    </button>
                  </div>
                </div>
              )}

              {tab === 'audio' && detalhe.hasAudio && (
                <div style={{ marginTop: 12 }}>
                  <audio controls style={{ width: '100%' }} src={recordingAudioUrl(sel)} />
                  <div className="muted" style={{ fontSize: 11, marginTop: 6 }}>{t('Áudio original da gravação.')}</div>
                </div>
              )}

              {sujo && (
                <div style={{ position: 'sticky', bottom: 0, marginTop: 10, paddingTop: 8, background: 'var(--card)' }}>
                  <button onClick={salvar} disabled={salvando}>{salvando ? t('Salvando...') : t('Salvar alterações')}</button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
