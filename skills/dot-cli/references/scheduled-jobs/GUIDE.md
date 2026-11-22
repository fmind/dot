---
name: scheduled-jobs
description: "Schedule/debug local jobs via systemd timers, launchd."
---

# Scheduled Jobs

Schedule bounded commands via native user schedulers and verify triggered runs ([python/script](../../../python/references/script/GUIDE.md) owns scripts; [mise](../../../mise/SKILL.md) owns tasks).

## Workflow

1. **Pick the native scheduler**: [Linux user timers](references/linux.md) or [macOS LaunchAgents](references/macos.md) (keep existing project schedulers unless migrating; host skills own harness-native schedules).
1. **Version definitions in the owning repo**: invoke an absolute executable path with locked dependencies and a single-writer lock; enable only after the user approves the schedule and recurring effects.
1. **Prove a real timer-triggered run** and its application outcome (manual runs or enabled units alone are partial proof).

## Gotchas

- **Stay in user space**: never use `sudo`, system units, or `loginctl enable-linger` unasked; note if requested availability exceeds logged-in sessions.
- **Handle missed or timed-out runs explicitly**: choose skip vs coalesce deliberately and reconcile current state before re-running mutations.

## Documentation

- [systemd timers](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html) · [systemd services](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html) · [Apple LaunchAgents](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html) · [Apple scheduled jobs](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html)
- Companions: [python/script](../../../python/references/script/GUIDE.md), [mise](../../../mise/SKILL.md), [dot-cli](../../SKILL.md).
