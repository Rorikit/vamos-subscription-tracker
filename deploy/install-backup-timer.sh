#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/vamos-subscription-tracker}"
BACKUP_INTERVAL_HOURS="${BACKUP_INTERVAL_HOURS:-6}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env}"
SERVICE_NAME="${SERVICE_NAME:-backend}"
BACKUP_PREFIX="${BACKUP_PREFIX:-prod-app}"

cat > /etc/systemd/system/vamos-backup.service <<EOF
[Unit]
Description=Vamos Subscription Tracker SQLite backup
Wants=network-online.target docker.service
After=network-online.target docker.service

[Service]
Type=oneshot
WorkingDirectory=$APP_DIR
Environment=APP_DIR=$APP_DIR
Environment=BACKUP_DIR=$BACKUP_DIR
Environment=RETENTION_DAYS=$RETENTION_DAYS
Environment=COMPOSE_FILE=$COMPOSE_FILE
Environment=ENV_FILE=$ENV_FILE
Environment=SERVICE_NAME=$SERVICE_NAME
Environment=BACKUP_PREFIX=$BACKUP_PREFIX
ExecStart=/usr/bin/env bash $APP_DIR/deploy/backup-sqlite.sh
EOF

cat > /etc/systemd/system/vamos-backup.timer <<EOF
[Unit]
Description=Run Vamos Subscription Tracker SQLite backup every $BACKUP_INTERVAL_HOURS hours

[Timer]
OnBootSec=10min
OnUnitActiveSec=${BACKUP_INTERVAL_HOURS}h
RandomizedDelaySec=10min
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now vamos-backup.timer
systemctl start vamos-backup.service

systemctl status vamos-backup.timer --no-pager
