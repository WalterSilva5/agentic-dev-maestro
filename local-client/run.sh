#!/bin/bash
# Maestro Local — script de execução
# Uso: ./run.sh [--port 8888]

set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv .venv
fi

source .venv/bin/activate

if ! python -c "import maestro_local" 2>/dev/null; then
    echo "Instalando dependencias..."
    pip install -e . --quiet
fi

exec python -m maestro_local "$@"
