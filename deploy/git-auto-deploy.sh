#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/vamos-subscription-tracker}"
BRANCH="${BRANCH:-main}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env}"

cd "$APP_DIR"

apply_caddy_bind_ip() {
  if [ -z "${CADDY_BIND_IP:-}" ]; then
    return 0
  fi

  python3 - <<PY
from pathlib import Path

compose_path = Path("$COMPOSE_FILE")
lines = compose_path.read_text().splitlines()
out = []
in_caddy = False
in_ports = False

for line in lines:
    if line.startswith("  caddy:"):
        in_caddy = True
        in_ports = False
        out.append(line)
        continue
    if in_caddy and line.startswith("  ") and not line.startswith("    ") and not line.startswith("  caddy:"):
        in_caddy = False
        in_ports = False
    if in_caddy and line.strip() == "ports:":
        out.append(line)
        out.append('      - "${CADDY_BIND_IP}:80:80"')
        out.append('      - "${CADDY_BIND_IP}:443:443"')
        in_ports = True
        continue
    if in_caddy and in_ports:
        if line.startswith("      - "):
            continue
        in_ports = False
    out.append(line)

compose_path.write_text("\\n".join(out) + "\\n")
PY
}

git fetch origin "$BRANCH"

current_commit="$(git rev-parse HEAD)"
remote_commit="$(git rev-parse "origin/$BRANCH")"

if [ "$current_commit" = "$remote_commit" ]; then
  apply_caddy_bind_ip
  echo "Already up to date: $current_commit"
  exit 0
fi

echo "Deploying $current_commit -> $remote_commit"
git reset --hard "$remote_commit"

apply_caddy_bind_ip

docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up --build -d

if docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps caddy >/dev/null 2>&1; then
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T caddy caddy reload --config /etc/caddy/Caddyfile || \
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart caddy
fi

if [ "${BOOTSTRAP_V1_STAGING:-true}" = "true" ] && [ "$APP_DIR" = "/opt/vamos-subscription-tracker" ]; then
  bash "$APP_DIR/deploy/bootstrap-v1-staging.sh"
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T caddy caddy reload --config /etc/caddy/Caddyfile || \
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart caddy
fi

if [ -f "$APP_DIR/deploy/vamos-backup.service" ] && [ -f "$APP_DIR/deploy/vamos-backup.timer" ]; then
  cp "$APP_DIR/deploy/vamos-backup.service" /etc/systemd/system/vamos-backup.service
  cp "$APP_DIR/deploy/vamos-backup.timer" /etc/systemd/system/vamos-backup.timer
  systemctl daemon-reload
  systemctl enable --now vamos-backup.timer
fi

docker image prune -f
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
