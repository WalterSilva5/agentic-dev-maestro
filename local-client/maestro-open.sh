#!/bin/bash
# Abre o Maestro desktop numa tela específica via links maestro://<tela>.
# Ex.: maestro://reunioes  ->  Reuniões (nativo: microfone/Whisper)
#      maestro://vault     ->  Senhas (nativo: cofre KeePass local)
# Uso (registrado via agentic-dev-maestro-url.desktop):
#     maestro-open "maestro://reunioes"
set -e

URL="${1:-maestro://reunioes}"
VIEW="$(printf '%s' "$URL" | sed -e 's#^maestro://##' -e 's#/.*##' -e 's#?.*##' | tr 'A-Z' 'a-z')"

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
  echo "maestro-open: sem sessão gráfica (DISPLAY/WAYLAND_DISPLAY ausentes)" >&2
  exit 1
fi

# Se o app já está rodando, apenas abre outra janela na tela pedida
# (o estado — workspace/projeto — é compartilhado via config.json).
exec "$APP_DIR/run.sh" --view "$VIEW"
