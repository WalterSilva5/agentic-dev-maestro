#!/bin/bash
# Maestro Local — instalação completa
# Cria venv, instala dependencias e valida a instalação

set -e
cd "$(dirname "$0")"

echo "=== Maestro Local — Instalação ==="
echo ""

# Python check
PYTHON=""
for cmd in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "Erro: Python 3.10+ nao encontrado."
    echo "Instale com: sudo pacman -S python  (Arch/Manjaro)"
    echo "             sudo apt install python3  (Debian/Ubuntu)"
    exit 1
fi

echo "Python: $($PYTHON --version)"

# Venv
if [ ! -d ".venv" ]; then
    echo "Criando ambiente virtual..."
    $PYTHON -m venv .venv
else
    echo "Ambiente virtual ja existe."
fi

source .venv/bin/activate
echo "Venv: $(which python)"

# Dependencias
echo "Instalando dependencias..."
pip install -e . --quiet

# Validação
echo ""
echo "Validando instalacao..."
python -c "
import maestro_local
from PySide6.QtWidgets import QApplication
from fastapi import FastAPI
print('  maestro_local: OK')
print('  PySide6: OK')
print('  FastAPI: OK')
"

echo ""
echo "=== Instalacao concluida ==="
echo ""
echo "Para executar:"
echo "  ./run.sh"
echo "  # ou"
echo "  source .venv/bin/activate && python -m maestro_local"
