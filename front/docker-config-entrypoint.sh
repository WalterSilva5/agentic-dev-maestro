#!/bin/sh
# Gera /usr/share/nginx/html/config.json em runtime a partir de variáveis de
# ambiente, permitindo configurar a app POR AMBIENTE sem rebuild da imagem.
# Roda automaticamente via /docker-entrypoint.d/ do nginx, antes de subir o server.
# Os defaults espelham o front/public/config.json versionado.
set -e

: "${API_URL:=/api}"
: "${PRODUCTION:=true}"
: "${APP_NAME:=Agentic Dev Maestro}"
: "${PRIMARY_COLOR:=#1DB954}"
: "${STATUS_BAR_COLOR:=#181818}"

cat > /usr/share/nginx/html/config.json <<EOF
{
  "apiUrl": "${API_URL}",
  "production": ${PRODUCTION},
  "app": {
    "name": "${APP_NAME}",
    "version": "1.0.0",
    "theme": {
      "primaryColor": "${PRIMARY_COLOR}",
      "statusBarColor": "${STATUS_BAR_COLOR}"
    }
  }
}
EOF

echo "[config] config.json gerado em runtime (apiUrl=${API_URL}, production=${PRODUCTION})"
