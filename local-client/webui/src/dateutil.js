/**
 * Data ISO no fuso LOCAL.
 *
 * `toISOString()` é UTC: às 21h no Brasil (UTC-3) ele já devolve o dia
 * seguinte, e a tela abria "amanhã" (dia sem registros).
 */
export function isoLocal(d = new Date()) {
  const ano = d.getFullYear()
  const mes = String(d.getMonth() + 1).padStart(2, '0')
  const dia = String(d.getDate()).padStart(2, '0')
  return `${ano}-${mes}-${dia}`
}
