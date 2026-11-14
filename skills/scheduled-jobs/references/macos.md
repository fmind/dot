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

Inspect existing labels before `bootstrap` (macOS 13+: check System Settings › General › Login Items & Extensions if BTM blocks it). Test with `launchctl kickstart "gui/$(id -u)/dev.example.report"` (omit `-k` unless killing active runs). `StartCalendarInterval` coalesces wake-from-sleep misses only; prove a real scheduled firing beyond `plutil`/`kickstart`, unload via `launchctl bootout`, and remove definitions in the owning repo.

Sources: [Apple LaunchAgents](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html) · [Scheduling](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html).
