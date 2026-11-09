#!/bin/bash
# Abre o Relay desktop numa tela específica via links relay://<tela>.
# Ex.: relay://reunioes  ->  Reuniões (nativo: microfone/Whisper)
#      relay://vault     ->  Senhas (nativo: cofre KeePass local)
# Uso (registrado via relay-url.desktop):
#     relay-open "relay://reunioes"
set -e

URL="${1:-relay://reunioes}"
VIEW="$(printf '%s' "$URL" | sed -e 's#^relay://##' -e 's#/.*##' -e 's#?.*##' | tr 'A-Z' 'a-z')"

case "$VIEW" in
  reunioes|transcricoes|meetings) VIEW=reunioes ;;
  vault|senhas|passwords)         VIEW=vault ;;
  config|settings|configuracoes)  VIEW=config ;;
  board|kanban)                   VIEW=board ;;
  *)                              VIEW=reunioes ;;
esac

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONUTF8=1

# Reaproveita a sessão gráfica; sem display, só registra o pedido.
if [ -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
  echo "relay-open: sem sessão gráfica (DISPLAY/WAYLAND_DISPLAY ausentes)" >&2
  exit 1
fi

# Se o app já está rodando, apenas abre outra janela na tela pedida
# (o estado — workspace/projeto — é compartilhado via config.json).
exec "$APP_DIR/run.sh" --view "$VIEW"
