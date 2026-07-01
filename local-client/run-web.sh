#!/bin/bash
# Maestro — roda apenas a API + web UI (sem a GUI desktop)
# Uso: ./run-web.sh [--port 9777]
set -e
cd "$(dirname "$0")"

export PYTHONUTF8=1
case "${LANG}${LC_ALL}" in
    *[Uu][Tt][Ff]*) : ;;
    *) export LANG=C.UTF-8 LC_ALL=C.UTF-8 ;;
esac

if [ ! -d ".venv" ]; then
    echo "Ambiente virtual não encontrado. Rode ./install.sh primeiro."
    exit 1
fi
source .venv/bin/activate

# Builda a web UI se ainda não houver bundle
if [ ! -f "webui/dist/index.html" ] && command -v npm &>/dev/null; then
    echo "Buildando a web UI..."
    (cd webui && npm install --silent && npm run build --silent)
fi

exec python -m maestro_local.webmain "$@"
