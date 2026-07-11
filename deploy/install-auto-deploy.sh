#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/vamos-subscription-tracker}"

cp "$APP_DIR/deploy/vamos-auto-deploy.service" /etc/systemd/system/vamos-auto-deploy.service
cp "$APP_DIR/deploy/vamos-auto-deploy.timer" /etc/systemd/system/vamos-auto-deploy.timer

systemctl daemon-reload
systemctl enable --now vamos-auto-deploy.timer
systemctl start vamos-auto-deploy.service

systemctl status vamos-auto-deploy.timer --no-pager
