#!/usr/bin/env bash
# Gera os .svg a partir dos .puml usando PlantUML.
# Requer Java + Graphviz (dot). Baixa o plantuml.jar na 1a execucao.
#   uso: ./gerar.sh
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JAR="$DIR/.plantuml.jar"

if [ ! -f "$JAR" ]; then
  # Resolve o jar (MIT) da release mais recente no GitHub. Pode-se forcar via
  # PLANTUML_URL=<url do .jar> ./gerar.sh
  URL="${PLANTUML_URL:-$(curl -fsSL https://api.github.com/repos/plantuml/plantuml/releases/latest \
        | grep -oE '"browser_download_url": *"[^"]*plantuml-mit-[0-9.]+\.jar"' \
        | head -1 | sed -E 's/.*"(https[^"]+)"/\1/')}"
  echo "Baixando PlantUML de: ${URL}"
  curl -fsSL "$URL" -o "$JAR"
fi

echo "Gerando SVGs..."
java -jar "$JAR" -tsvg "$DIR"/*.puml
echo "OK — $(ls "$DIR"/*.svg 2>/dev/null | wc -l) diagramas em $DIR"
