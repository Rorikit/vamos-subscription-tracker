#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/vamos-subscription-tracker}"
BRANCH="${BRANCH:-main}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env}"

cd "$APP_DIR"

git fetch origin "$BRANCH"

current_commit="$(git rev-parse HEAD)"
remote_commit="$(git rev-parse "origin/$BRANCH")"

if [ "$current_commit" = "$remote_commit" ]; then
  echo "Already up to date: $current_commit"
  exit 0
fi

echo "Deploying $current_commit -> $remote_commit"
git reset --hard "$remote_commit"

docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up --build -d

if [ "${BOOTSTRAP_V1_STAGING:-true}" = "true" ] && [ "$APP_DIR" = "/opt/vamos-subscription-tracker" ]; then
  bash "$APP_DIR/deploy/bootstrap-v1-staging.sh"
fi

if [ -f "$APP_DIR/deploy/vamos-backup.service" ] && [ -f "$APP_DIR/deploy/vamos-backup.timer" ]; then
  cp "$APP_DIR/deploy/vamos-backup.service" /etc/systemd/system/vamos-backup.service
  cp "$APP_DIR/deploy/vamos-backup.timer" /etc/systemd/system/vamos-backup.timer
  systemctl daemon-reload
  systemctl enable --now vamos-backup.timer
fi

docker image prune -f
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
