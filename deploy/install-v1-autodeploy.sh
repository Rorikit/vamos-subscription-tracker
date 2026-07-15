#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/vamos-subscription-tracker-v1}"

cp "$APP_DIR/deploy/vamos-v1-auto-deploy.service" /etc/systemd/system/vamos-v1-auto-deploy.service
cp "$APP_DIR/deploy/vamos-v1-auto-deploy.timer" /etc/systemd/system/vamos-v1-auto-deploy.timer

systemctl daemon-reload
systemctl enable --now vamos-v1-auto-deploy.timer
systemctl start vamos-v1-auto-deploy.service

systemctl status vamos-v1-auto-deploy.timer --no-pager
