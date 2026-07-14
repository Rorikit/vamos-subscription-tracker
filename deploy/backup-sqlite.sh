#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/vamos-subscription-tracker}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env}"
LOCK_FILE="${LOCK_FILE:-/tmp/vamos-sqlite-backup.lock}"

mkdir -p "$BACKUP_DIR"

(
  flock -n 9

  cd "$APP_DIR"

  timestamp="$(date +%Y%m%d-%H%M%S)"
  backup_file="$BACKUP_DIR/app-$timestamp.db.gz"

  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend python - <<'PY' | gzip -c > "$backup_file"
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

source_path = Path("/app/data/app.db")
if not source_path.exists():
    raise SystemExit("SQLite database does not exist: /app/data/app.db")

with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
    temp_path = Path(temp_file.name)

try:
    source = sqlite3.connect(str(source_path))
    target = sqlite3.connect(str(temp_path))
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()

    sys.stdout.buffer.write(temp_path.read_bytes())
finally:
    try:
        os.remove(temp_path)
    except FileNotFoundError:
        pass
PY

  chmod 600 "$backup_file"
  find "$BACKUP_DIR" -type f -name "app-*.db.gz" -mtime +"$RETENTION_DAYS" -delete

  echo "Created backup: $backup_file"
  ls -lh "$backup_file"
) 9>"$LOCK_FILE"
