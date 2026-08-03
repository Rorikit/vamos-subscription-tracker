#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/vamos-subscription-tracker}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env}"
SERVICE_NAME="${SERVICE_NAME:-backend}"
BACKUP_FILE="${1:-}"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 /path/to/backup.db.gz" >&2
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE" >&2
  exit 1
fi

if [ -f "$BACKUP_FILE.sha256" ]; then
  sha256sum -c "$BACKUP_FILE.sha256"
fi

cd "$APP_DIR"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop "$SERVICE_NAME"
gzip -dc "$BACKUP_FILE" > /tmp/vamos-restore-app.db
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" run --rm -T "$SERVICE_NAME" sh -c 'mkdir -p /app/data && cat > /app/data/app.db' < /tmp/vamos-restore-app.db
rm -f /tmp/vamos-restore-app.db
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d "$SERVICE_NAME"
echo "Restored backup: $BACKUP_FILE"
