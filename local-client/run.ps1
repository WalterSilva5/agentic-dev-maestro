# Maestro Local — script de execução (Windows / PowerShell)
# Equivalente ao run.sh.
# Uso: .\run.ps1 [--port 8888]

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# Modo UTF-8 (evita erros de decodificação na transcrição em locales não-UTF8)
$env:PYTHONUTF8 = "1"

if (-not (Test-Path ".venv")) {
    Write-Host "Criando ambiente virtual..."
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv .venv }
    else { & python -m venv .venv }
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Erro: ambiente virtual inválido. Rode .\install.ps1 primeiro." -ForegroundColor Red
    exit 1
}

& $venvPython -c "import maestro_local" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Instalando dependencias..."
    & $venvPython -m pip install -e . --quiet
}

& $venvPython -m maestro_local @args
