# Maestro Local — instalação completa (Windows / PowerShell)
# Equivalente ao install.sh: cria venv, instala dependências e valida.
#
# Uso (PowerShell):
#   .\install.ps1
# Se a execução de scripts estiver bloqueada:
#   powershell -ExecutionPolicy Bypass -File .\install.ps1

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "=== Maestro Local — Instalação ===" -ForegroundColor Cyan
Write-Host ""

# --- Python ---
$python = $null
# 'py -3' é o launcher oficial do Windows; cai para 'python' se não existir.
if (Get-Command py -ErrorAction SilentlyContinue) {
    try {
        & py -3 --version *> $null
        if ($LASTEXITCODE -eq 0) { $python = "py"; $pyArgs = @("-3") }
    } catch { }
}
if (-not $python -and (Get-Command python -ErrorAction SilentlyContinue)) {
    $python = "python"; $pyArgs = @()
}
if (-not $python) {
    Write-Host "Erro: Python 3.10+ nao encontrado." -ForegroundColor Red
    Write-Host "Instale em https://www.python.org/downloads/ (marque 'Add python.exe to PATH')"
    Write-Host "ou pela Microsoft Store: winget install Python.Python.3.12"
    exit 1
}

$version = & $python @pyArgs --version
Write-Host "Python: $version"

# --- Venv ---
if (-not (Test-Path ".venv")) {
    Write-Host "Criando ambiente virtual..."
    & $python @pyArgs -m venv .venv
} else {
    Write-Host "Ambiente virtual já existe."
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Erro: venv criado mas $venvPython não existe." -ForegroundColor Red
    exit 1
}
Write-Host "Venv: $venvPython"

# --- Dependências ---
Write-Host "Instalando dependências..."
& $venvPython -m pip install --upgrade pip --quiet
& $venvPython -m pip install -e . --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "Erro ao instalar as dependências." -ForegroundColor Red
    exit 1
}

# --- Validação ---
Write-Host ""
Write-Host "Validando instalação..."
$checks = @(
    @("maestro_local", "import maestro_local"),
    @("PySide6",       "from PySide6.QtWidgets import QApplication"),
    @("FastAPI",       "from fastapi import FastAPI")
)
foreach ($check in $checks) {
    & $venvPython -c $check[1]
    if ($LASTEXITCODE -ne 0) {
        Write-Host ("  {0}: FALHOU" -f $check[0]) -ForegroundColor Red
        Write-Host "Erro na validação da instalação." -ForegroundColor Red
        exit 1
    }
    Write-Host ("  {0}: OK" -f $check[0])
}

# --- Web UI (opcional) ---
if (Get-Command npm -ErrorAction SilentlyContinue) {
    Write-Host ""
    Write-Host "Buildando a web UI (webui)..."
    Push-Location webui
    try {
        & npm install --silent
        & npm run build --silent
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  web UI: OK (disponível em http://127.0.0.1:9777/)"
        } else {
            Write-Host "  web UI: falhou o build (a API segue funcionando; rode 'cd webui; npm install; npm run build')"
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Host ""
    Write-Host "npm não encontrado — pulando build da web UI (só a GUI desktop). Instale o Node para habilitar o frontend web."
}

Write-Host ""
Write-Host "=== Instalação concluída ===" -ForegroundColor Green
Write-Host ""
Write-Host "Para executar:"
Write-Host "  .\run.ps1"
Write-Host "  # ou"
Write-Host "  .venv\Scripts\python.exe -m maestro_local"
Write-Host ""
Write-Host "Nota: a gravação de Reuniões usa o parec/PulseAudio e funciona no Linux." -ForegroundColor Yellow
Write-Host "No Windows o app roda normalmente (board, IA, importar transcrições do"
Write-Host "Meet/Teams, etc.), mas a captura de áudio da reunião fica indisponível."
