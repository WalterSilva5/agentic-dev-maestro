#!/bin/bash
#
# Backup do banco de dados MySQL
# Le as credenciais do arquivo .env (DATABASE_URL)
# Salva os backups em database-backups/ com timestamp
#

set -euo pipefail

# Diretorio do projeto (raiz do repo)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/database-backups"
ENV_FILE="$PROJECT_DIR/.env"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERRO]${NC} $1"; }

# Verificar se .env existe
if [ ! -f "$ENV_FILE" ]; then
  log_error "Arquivo .env nao encontrado em: $ENV_FILE"
  exit 1
fi

# Ler DATABASE_URL do .env
DATABASE_URL=$(grep -E '^DATABASE_URL=' "$ENV_FILE" | head -1 | cut -d'=' -f2- | tr -d '"' | tr -d "'")

if [ -z "$DATABASE_URL" ]; then
  log_error "DATABASE_URL nao encontrada no .env"
  exit 1
fi

# Parsear a URL de conexao
# Formato: mysql://USER:PASSWORD@HOST:PORT/DATABASE
# Tambem suporta: mysql://USER:PASSWORD@HOST/DATABASE (sem porta)
PROTO=$(echo "$DATABASE_URL" | grep -oP '^[a-z]+(?=://)')
if [ "$PROTO" != "mysql" ] && [ "$PROTO" != "mysql2" ]; then
  log_error "Protocolo nao suportado: $PROTO (esperado: mysql)"
  exit 1
fi

# Extrair componentes da URL
URL_BODY=$(echo "$DATABASE_URL" | sed 's|^[a-z2]*://||')

# Separar credenciais do host
USER_PASS=$(echo "$URL_BODY" | cut -d'@' -f1)
HOST_DB=$(echo "$URL_BODY" | cut -d'@' -f2)

DB_USER=$(echo "$USER_PASS" | cut -d':' -f1)
DB_PASS=$(echo "$USER_PASS" | cut -d':' -f2-)

# Separar host:port do database
HOST_PORT=$(echo "$HOST_DB" | cut -d'/' -f1)
DB_NAME=$(echo "$HOST_DB" | cut -d'/' -f2 | cut -d'?' -f1)

# Separar host e porta
if echo "$HOST_PORT" | grep -q ':'; then
  DB_HOST=$(echo "$HOST_PORT" | cut -d':' -f1)
  DB_PORT=$(echo "$HOST_PORT" | cut -d':' -f2)
else
  DB_HOST="$HOST_PORT"
  DB_PORT="3306"
fi

# Validar campos
if [ -z "$DB_USER" ] || [ -z "$DB_HOST" ] || [ -z "$DB_NAME" ]; then
  log_error "Nao foi possivel parsear DATABASE_URL"
  log_error "Formato esperado: mysql://USER:PASSWORD@HOST:PORT/DATABASE"
  exit 1
fi

# Verificar se mysqldump esta instalado
if ! command -v mysqldump &>/dev/null; then
  log_error "mysqldump nao encontrado. Instale o client MySQL:"
  log_error "  sudo pacman -S mariadb-clients   # Arch/Manjaro"
  log_error "  sudo apt install mysql-client     # Debian/Ubuntu"
  exit 1
fi

# Criar diretorio de backups
mkdir -p "$BACKUP_DIR"

# Gerar nome do arquivo com timestamp
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"

log_info "Iniciando backup..."
log_info "  Host:     $DB_HOST:$DB_PORT"
log_info "  Database: $DB_NAME"
log_info "  Usuario:  $DB_USER"
log_info "  Destino:  $BACKUP_FILE"

# Executar backup com compressao gzip
export MYSQL_PWD="$DB_PASS"

# Detectar comando de dump: mariadb-dump (MariaDB) ou mysqldump (MySQL)
DUMP_CMD=""
DUMP_EXTRA_OPTS=""

if command -v mariadb-dump &>/dev/null; then
  DUMP_CMD="mariadb-dump"
  log_info "Detectado: mariadb-dump"
elif command -v mysqldump &>/dev/null; then
  # Verificar se e MariaDB disfarçado de mysqldump
  if mysqldump --version 2>&1 | grep -qi "mariadb\|Deprecated"; then
    DUMP_CMD="mysqldump"
    log_info "Detectado: mysqldump (MariaDB compat)"
  else
    DUMP_CMD="mysqldump"
    DUMP_EXTRA_OPTS="--set-gtid-purged=OFF --column-statistics=0"
    log_info "Detectado: mysqldump (MySQL)"
  fi
else
  log_error "Nenhum comando de dump encontrado (mariadb-dump ou mysqldump)"
  exit 1
fi

DUMP_ERROR_FILE=$(mktemp)

if $DUMP_CMD \
  --host="$DB_HOST" \
  --port="$DB_PORT" \
  --user="$DB_USER" \
  --single-transaction \
  --routines \
  --triggers \
  $DUMP_EXTRA_OPTS \
  "$DB_NAME" 2>"$DUMP_ERROR_FILE" | gzip > "$BACKUP_FILE"; then

  unset MYSQL_PWD

  # Verificar se o arquivo foi criado e nao esta vazio
  # gzip de um dump vazio gera ~20 bytes, entao verificamos tamanho minimo
  FILESIZE_BYTES=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || echo "0")
  if [ "$FILESIZE_BYTES" -gt 100 ]; then
    FILESIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log_info "Backup concluido: $BACKUP_FILE ($FILESIZE)"
    rm -f "$DUMP_ERROR_FILE"
  else
    log_error "Arquivo de backup vazio ou muito pequeno"
    if [ -s "$DUMP_ERROR_FILE" ]; then
      log_error "Detalhes do mysqldump:"
      cat "$DUMP_ERROR_FILE" >&2
    fi
    rm -f "$BACKUP_FILE" "$DUMP_ERROR_FILE"
    exit 1
  fi
else
  unset MYSQL_PWD
  log_error "Falha ao executar mysqldump"
  if [ -s "$DUMP_ERROR_FILE" ]; then
    log_error "Detalhes:"
    cat "$DUMP_ERROR_FILE" >&2
  fi
  rm -f "$BACKUP_FILE" "$DUMP_ERROR_FILE"
  exit 1
fi

# Limpar backups antigos (manter ultimos 10)
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -type f | wc -l)
if [ "$BACKUP_COUNT" -gt 10 ]; then
  REMOVE_COUNT=$((BACKUP_COUNT - 10))
  log_warn "Removendo $REMOVE_COUNT backup(s) antigo(s) (mantendo 10 mais recentes)"
  find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -type f -printf '%T@ %p\n' \
    | sort -n \
    | head -n "$REMOVE_COUNT" \
    | cut -d' ' -f2- \
    | xargs rm -f
fi

log_info "Backups disponiveis:"
ls -lh "$BACKUP_DIR"/${DB_NAME}_*.sql.gz 2>/dev/null | awk '{print "  " $NF " (" $5 ")"}'
