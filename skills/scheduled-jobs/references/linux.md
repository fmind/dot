# Linux User Timers

Verify directives against installed `systemctl --version` and `man systemd.{timer,service}`. Use `systemctl --user` without `sudo` or silent lingering, keeping paired `<name>.service` and `<name>.timer` in the repo (`dot_config/systemd/user/` -> `~/.config/systemd/user/`):

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

On `Type=oneshot`, bound runtime with `TimeoutStartSec` (`RuntimeMaxSec` ignores oneshot activation) and keep default `OOMPolicy=stop` (`continue` is for long-lived daemons). `Persistent=true` coalesces missed triggers into one catch-up run; omit when unwanted. Override units via drop-ins (`~/.config/systemd/user/<unit>.d/<name>.conf`), clearing list keys (`ExecStart=`, `OnCalendar=`) with an empty line before reassigning, and verify via `systemctl --user show <unit> -p DropInPaths -p <Setting>`.

```bash
# Test cleanly inside the user manager (returns exit status):
systemd-run --user --wait --pipe --collect -p WorkingDirectory="$HOME/projects/example" -- "$HOME/.local/bin/mise" run report
systemd-analyze --user verify report.service report.timer
systemd-analyze calendar '*-*-* 09:00:00 Europe/Paris'
# Enable after authorization and deployment:
systemctl --user daemon-reload && systemctl --user enable --now report.timer
systemctl --user list-timers --all report.timer
systemctl --user show report.service -p Result -p ExecMainStatus -p ExecMainStartTimestamp -p ExecMainExitTimestamp
journalctl --user -u report.service -n 50 --no-pager
```

Test missing env, nonzero exit, timeout, and lock contention (timers skip active services, but manual runs still need a lock). `systemctl --user disable --now report.timer` stops future triggers without killing an active service; stop manually only within scope.
