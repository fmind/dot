# macOS LaunchAgents

Use a per-user LaunchAgent for a logged-in user. Check the installed `man launchctl` and `man launchd.plist`; Apple's archived guides explain the model but do not establish current CLI behavior. Keep the plist in its source repository and deploy to `~/Library/LaunchAgents/` through its configuration manager.

Generate the plist with Python `plistlib` when templating it, so XML values are escaped correctly. Define these fields from the actual job:

| Field | Contract |
| --- | --- |
| `Label` | Stable unique name, such as `dev.example.report` |
| `ProgramArguments` | Array of literal arguments starting with an absolute executable path; no shell command string |
| `WorkingDirectory` | Absolute project directory |
| `EnvironmentVariables` | Only required non-secret values; login-shell setup is not inherited |
| `StartCalendarInterval` | Explicit `Hour` and `Minute` values for a daily local-time schedule |
| `StandardOutPath`, `StandardErrorPath` | Separate bounded/rotated log destinations in an existing user-owned directory |

Resolve home-relative source values to absolute paths when generating the plist: `~`, `$HOME`, globbing, and shell substitution do not expand in `ProgramArguments`. Keep `KeepAlive` and `RunAtLoad` absent unless their extra executions are part of the requested behavior. Bound the actual command in application code; `ExitTimeOut` is a shutdown grace period, not a job runtime limit.

```bash
plutil -lint "$HOME/Library/LaunchAgents/dev.example.report.plist"
# After authorization and deployment:
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/dev.example.report.plist"
launchctl print "gui/$(id -u)/dev.example.report"
```

Inspect an existing label before bootstrap; do not repeatedly unload/reload it to hide a configuration failure. An explicitly authorized manual start uses `launchctl kickstart "gui/$(id -u)/dev.example.report"`; omit `-k`, which would kill a running instance. For updates, account for the active run before bootout and bootstrap.

Apple documents wake-time catch-up for `StartCalendarInterval`, but not replay of jobs missed while powered off. Verify the deployed OS and login/sleep behavior with a harmless fixture. Do not claim that plist validation or kickstart proves a scheduled wake-up.

Stopping uses `launchctl bootout "gui/$(id -u)/dev.example.report"` within the authorized cancellation scope; it may affect a running process. Prevent future loading by removing only the owned deployed definition through its source configuration manager. Preserve logs and reconcile any uncertain write before rescheduling.

Sources: [Apple LaunchAgents](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html) and [scheduling](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html).
