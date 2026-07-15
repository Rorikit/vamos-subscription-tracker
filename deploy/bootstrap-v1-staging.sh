#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/vamos-subscription-tracker-v1}"
REPO_URL="${REPO_URL:-https://github.com/Rorikit/vamos-subscription-tracker.git}"
BRANCH="${BRANCH:-develop}"
PUBLIC_ORIGIN="${PUBLIC_ORIGIN:-http://168.222.140.16}"
PASSWORD_FILE="${PASSWORD_FILE:-/root/vamos-v1-operator-password.txt}"
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-vamos-v1}"

if [ ! -d "$APP_DIR/.git" ]; then
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"

if [ ! -f .env.v1 ]; then
  auth_secret="$(openssl rand -hex 32)"
  operator_password="$(openssl rand -base64 18 | tr -d '=+/')"
  cat > .env.v1 <<EOF
DATABASE_URL=sqlite:///./data/app.db
CORS_ORIGINS=$PUBLIC_ORIGIN

AUTH_SECRET=$auth_secret
AUTH_TOKEN_TTL_HOURS=24
SEED_DEMO_DATA=true
OPERATOR_USERNAME=operator
OPERATOR_PASSWORD=$operator_password
OPERATOR_FULL_NAME=Operator Vamos V1

VITE_API_URL=/v1/api
VITE_BASE_PATH=/v1/
EOF
  chmod 600 .env.v1
  printf "%s\n" "$operator_password" > "$PASSWORD_FILE"
  chmod 600 "$PASSWORD_FILE"
fi

docker compose -f docker-compose.v1.yml --env-file .env.v1 up --build -d

cp "$APP_DIR/deploy/vamos-v1-auto-deploy.service" /etc/systemd/system/vamos-v1-auto-deploy.service
cp "$APP_DIR/deploy/vamos-v1-auto-deploy.timer" /etc/systemd/system/vamos-v1-auto-deploy.timer
systemctl daemon-reload
systemctl enable --now vamos-v1-auto-deploy.timer

docker compose -f docker-compose.v1.yml --env-file .env.v1 ps
