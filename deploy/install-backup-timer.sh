#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/vamos-subscription-tracker}"

cp "$APP_DIR/deploy/vamos-backup.service" /etc/systemd/system/vamos-backup.service
cp "$APP_DIR/deploy/vamos-backup.timer" /etc/systemd/system/vamos-backup.timer

systemctl daemon-reload
systemctl enable --now vamos-backup.timer
systemctl start vamos-backup.service

systemctl status vamos-backup.timer --no-pager
