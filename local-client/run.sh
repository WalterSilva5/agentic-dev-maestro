#!/bin/bash
# Maestro Local — script de execução
# Uso: ./run.sh [--port 8888]

set -e
cd "$(dirname "$0")"

# Garante modo UTF-8 (evita UnicodeDecodeError na transcrição quando
# iniciado em ambientes com locale ascii, como autostart)
export PYTHONUTF8=1
case "${LANG}${LC_ALL}" in
    *[Uu][Tt][Ff]*) : ;;                 # já é UTF-8, mantém
    *) export LANG=C.UTF-8 LC_ALL=C.UTF-8 ;;
esac

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
