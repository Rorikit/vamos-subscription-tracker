# Security Operations

## Backup Policy

Production SQLite backups are created by `vamos-backup.timer`.

Default policy:

- interval: every 6 hours;
- retention: 30 days when installed through `deploy/install-backup-timer.sh`;
- storage: `/opt/vamos-subscription-tracker/backups`;
- format: `prod-app-YYYYmmdd-HHMMSS.db.gz`;
- integrity file: `.sha256` next to every archive.

Install or update timer:

```bash
cd /opt/vamos-subscription-tracker
BACKUP_INTERVAL_HOURS=6 RETENTION_DAYS=30 bash deploy/install-backup-timer.sh
```

Manual backup:

```bash
systemctl start vamos-backup.service
```

Check timer:

```bash
systemctl list-timers vamos-backup.timer
journalctl -u vamos-backup.service -n 100 --no-pager
ls -lh /opt/vamos-subscription-tracker/backups
```

Restore:

```bash
cd /opt/vamos-subscription-tracker
bash deploy/restore-sqlite-backup.sh /opt/vamos-subscription-tracker/backups/prod-app-YYYYmmdd-HHMMSS.db.gz
```

Always test restore on staging before restoring production.

## Immediate Security Priorities

1. Rotate all credentials that were ever sent in chat or stored in plain text.
2. Disable SSH password login and keep only SSH key access.
3. Keep `root` access for emergency only; create a separate sudo user for operations.
4. Use unique strong values for `AUTH_SECRET`, `OPERATOR_PASSWORD`, and `ROOT_OPERATOR_PASSWORD`.
5. Store `.env` with `chmod 600` and do not commit it.
6. Keep production `SEED_DEMO_DATA=false`.
7. Keep only ports `80`, `443`, and SSH open; backend must stay internal to Docker.
8. Enable automatic security updates on the VPS.
9. Keep backups off-server as a second copy. Local server backups protect against app mistakes, not VPS loss.
10. Review `journalctl`, Caddy logs, and Docker logs after each deploy.

## Recommended Next Steps

- Add off-site backup sync to S3, Backblaze B2, Google Drive, or another external storage.
- Add a daily restore check on staging.
- Add audit alerts for login failures and destructive operations.
- Add account lockout or rate limiting for `/auth/login`.
- Add database migration tooling before switching from SQLite to PostgreSQL.
- Add HTTPS domain instead of IP-only access.
