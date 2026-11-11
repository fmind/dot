# macOS LaunchAgents

Check installed `man launchctl` and `man launchd.plist`, version the plist in its source repo, and deploy to `~/Library/LaunchAgents/`. Generate templated plists via Python `plistlib` with a reverse-DNS `Label` (`dev.example.report`), absolute `WorkingDirectory`, and bounded log paths:

| Field                   | Contract                                                                                  |
| ----------------------- | ----------------------------------------------------------------------------------------- |
| `ProgramArguments`      | Literal arg array starting with an absolute executable (`~`, `$HOME`, globs never expand) |
| `EnvironmentVariables`  | Explicit non-secret env vars only (login shell is not inherited)                          |
| `StartCalendarInterval` | Explicit `Hour` and `Minute` for daily local-time runs                                    |

Omit `KeepAlive` and `RunAtLoad` unless requested, and enforce runtime timeouts inside the app (`ExitTimeOut` is shutdown grace only).

```bash
plutil -lint "$HOME/Library/LaunchAgents/dev.example.report.plist"
# After authorization and deployment:
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/dev.example.report.plist"
launchctl print "gui/$(id -u)/dev.example.report"
```

Inspect existing labels before `bootstrap` (on macOS 13+, check System Settings › General › Login Items & Extensions if Background Task Management blocks it). Run authorized manual tests with `launchctl kickstart "gui/$(id -u)/dev.example.report"` (omit `-k` unless killing an active run is intended). `StartCalendarInterval` coalesces wake-from-sleep misses, not power-off misses; prove a real scheduled firing rather than treating `plutil` or `kickstart` as complete proof. Stop within scope via `launchctl bootout "gui/$(id -u)/dev.example.report"` after checking in-flight runs, and remove definitions through the source config manager.

Sources: [Apple LaunchAgents](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html) · [Scheduling](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html).
