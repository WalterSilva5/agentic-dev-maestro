#!/bin/bash
# Maestro web — garante a API + web UI no ar e abre no navegador.
# Uso: ./maestro-web.sh [--port 9777]
set -e
cd "$(dirname "$0")"

PORT=9777
for i in "$@"; do
  case "$i" in
    --port=*) PORT="${i#*=}" ;;
    -p) shift_next=1 ;;
    *) if [ "${shift_next:-0}" = 1 ]; then PORT="$i"; shift_next=0; fi ;;
  esac
done
export MAESTRO_WEB_PORT="$PORT"

# Sobe a API + web UI em background se ainda não estiver respondendo.
if ! curl -s --max-time 2 "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
  if [ ! -d ".venv" ]; then
    echo "Ambiente virtual não encontrado. Rode ./install.sh primeiro."
    exit 1
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  if [ ! -f "webui/dist/index.html" ] && command -v npm &>/dev/null; then
    echo "Buildando a web UI..."
    (cd webui && npm install --silent && npm run build --silent)
  fi
  nohup python -m maestro_local.webmain --port "$PORT" >/tmp/maestro-web.log 2>&1 &
  disown
  echo "Aguardando a API em http://127.0.0.1:${PORT} ..."
  for _ in $(seq 1 40); do
    sleep 0.5
    curl -s --max-time 2 "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1 && break
  done
fi

URL="http://127.0.0.1:${PORT}/"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
  open "$URL" >/dev/null 2>&1 &
else
  echo "Abra no navegador: $URL"
fi
