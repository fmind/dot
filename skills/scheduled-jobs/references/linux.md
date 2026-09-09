# Linux User Timers

Check installed `systemd --version` and `man systemd.timer` / `man systemd.service`; installed documentation owns supported directives. Use `systemctl --user`, without sudo. A user manager may stop at logout; do not silently enable lingering.

Keep the service and timer in the job's source repository and deploy them to `~/.config/systemd/user/` using its existing configuration manager. Adapt this example's paths, timezone, interval, and limit to the job; replace the illustrative command with a real task before validation.

```ini
# https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
[Unit]
Description=Refresh the project report

[Service]
Type=oneshot
WorkingDirectory=%h/projects/example
ExecStart=%h/.local/bin/mise run report
TimeoutStartSec=10min
StandardOutput=journal
StandardError=journal
```

```ini
# https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html
[Unit]
Description=Refresh the project report daily

[Timer]
OnCalendar=*-*-* 09:00:00 Europe/Paris
Persistent=true

[Install]
WantedBy=timers.target
```

For `Type=oneshot`, `TimeoutStartSec` bounds the command; do not substitute `RuntimeMaxSec`, which does not bound oneshot activation. `Persistent=true` catches up a missed calendar trigger when the timer becomes active, rather than replaying each missed occurrence. Omit catch-up when inappropriate. Use the same basename, such as `report.service` and `report.timer`.

```bash
systemd-analyze --user verify report.service report.timer
systemd-analyze calendar '*-*-* 09:00:00 Europe/Paris'
# After authorization and deployment of these definitions:
systemctl --user daemon-reload
systemctl --user enable --now report.timer
systemctl --user list-timers --all report.timer
systemctl --user show report.service -p Result -p ExecMainStatus -p ExecMainStartTimestamp -p ExecMainExitTimestamp
journalctl --user -u report.service -n 50 --no-pager
```

Verify the expected application result for the same run. Test missing environment, nonzero exit, timeout, and lock contention with a harmless fixture before relying on unattended operation. A timer does not restart an already-active target service, but separate entry points still need the application's lock.

To stop an authorized job, use `systemctl --user disable --now report.timer`; this does not stop an active service. Inspect it, then use `systemctl --user stop report.service` when cancellation is in scope and reconcile any in-flight effect. Avoid automatic restarts of uncertain writes.
