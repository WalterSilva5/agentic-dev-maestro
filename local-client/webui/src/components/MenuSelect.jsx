import { useEffect, useRef, useState } from 'react'
import { t } from '../i18n'

/**
 * Seletor do menu lateral (workspace / projeto).
 *
 * Substitui o `<select>` nativo: mostra ícone (ou a chave do projeto), nome e
 * uma linha de apoio, e abre um popover com a lista. Como é web, o menu pode
 * usar a largura toda em vez de espremer um combo de 200px.
 */
export default function MenuSelect({
  label, value, options = [], onChange, placeholder,
  onCreate, createTitle, searchable = true, emptyHint,
}) {
  const [aberto, setAberto] = useState(false)
  const [busca, setBusca] = useState('')
  const raiz = useRef(null)

  useEffect(() => {
    if (!aberto) return undefined
    const fora = (e) => {
      if (raiz.current && !raiz.current.contains(e.target)) setAberto(false)
    }
    const esc = (e) => e.key === 'Escape' && setAberto(false)
    document.addEventListener('mousedown', fora)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', fora)
      document.removeEventListener('keydown', esc)
    }
  }, [aberto])

  useEffect(() => {
    if (!aberto) setBusca('')
  }, [aberto])

  const atual = options.find((o) => String(o.value) === String(value))
  const termo = busca.trim().toLowerCase()
  const lista = termo
    ? options.filter((o) => `${o.label} ${o.hint || ''}`.toLowerCase().includes(termo))
    : options

  const escolher = (v) => {
    setAberto(false)
    if (String(v) !== String(value)) onChange(v)
  }

  return (
    <div className="msel" ref={raiz}>
      <div className="msel-top">
        <span className="msel-label">{label}</span>
        {onCreate && (
          <button type="button" className="msel-add" onClick={onCreate} title={createTitle}>
            +
          </button>
        )}
      </div>

      <button
        type="button"
        className={`msel-btn${aberto ? ' open' : ''}${atual ? '' : ' empty'}`}
        onClick={() => setAberto((v) => !v)}
        aria-expanded={aberto}
      >
        {atual?.icon && <span className="msel-ico">{atual.icon}</span>}
        {atual?.badge && <span className="msel-badge">{atual.badge}</span>}
        <span className="msel-txt">
          <span className="msel-name">{atual?.label || placeholder || t('Selecione')}</span>
          {atual?.hint && <span className="msel-hint">{atual.hint}</span>}
        </span>
        <span className="msel-caret" aria-hidden="true">▾</span>
      </button>

      {aberto && (
        <div className="msel-pop" role="listbox">
          {searchable && options.length > 5 && (
            <input
              autoFocus
              className="msel-search"
              placeholder={t('Buscar...')}
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
            />
          )}
          <div className="msel-list">
            {lista.map((o) => {
              const ativo = String(o.value) === String(value)
              return (
                <button
                  type="button"
                  key={o.value}
                  role="option"
                  aria-selected={ativo}
                  className={`msel-item${ativo ? ' active' : ''}`}
                  onClick={() => escolher(o.value)}
                >
                  {o.icon && <span className="msel-ico">{o.icon}</span>}
                  {o.badge && <span className="msel-badge">{o.badge}</span>}
                  <span className="msel-txt">
                    <span className="msel-name">{o.label}</span>
                    {o.hint && <span className="msel-hint">{o.hint}</span>}
                  </span>
                  {ativo && <span className="msel-check">✓</span>}
                </button>
              )
            })}
            {lista.length === 0 && (
              <div className="msel-empty">{emptyHint || t('Nada encontrado')}</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
