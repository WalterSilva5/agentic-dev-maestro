import { CATALOG } from './i18n_catalog'

// Idioma-fonte é o português; t(pt) devolve a tradução quando o idioma é "en".
let _lang = 'pt'

export function setLang(l) {
  _lang = l === 'en' ? 'en' : 'pt'
}
export function getLang() {
  return _lang
}

export function t(s) {
  if (_lang === 'pt') return s
  return (CATALOG[_lang] && CATALOG[_lang][s]) || s
}

// Traduz e formata com {placeholders}: tf("Olá {name}", {name:"x"})
export function tf(s, vars = {}) {
  let out = t(s)
  for (const [k, v] of Object.entries(vars)) out = out.replaceAll(`{${k}}`, v)
  return out
}
