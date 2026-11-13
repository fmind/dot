---
name: scheduled-jobs
description: "Schedule and debug local jobs with systemd timers or macOS launchd."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/scheduled-jobs
  created: "2026-09-09"
  updated: "2026-11-13"
---

# Scheduled Jobs

Schedule bounded commands via native user schedulers and verify triggered runs ([python-script](../python-stack/references/python-script/GUIDE.md) owns scripts; [mise](../mise/SKILL.md) owns tasks).

## Workflow

1. **Pick the native scheduler**: [Linux user timers](references/linux.md) or [macOS LaunchAgents](references/macos.md) (keep existing project schedulers unless migrating; host skills own harness-native schedules).
1. **Version definitions in the owning repo**: invoke an absolute executable path with locked dependencies and a single-writer lock; enable only after the user approves the schedule and recurring effects.
1. **Prove a real timer-triggered run** and its application outcome (manual runs or enabled units alone are partial proof).

## Owner conventions

- **`fmind/dot` user units (Linux only)**: store in `dot_config/systemd/user/`, enable via `timers.target.wants` symlinks, and register unit hashes in `run_onchange_after_systemd-user-reload.sh.tmpl` (`systemctl --user daemon-reload` on apply; ignored outside Linux).
- **Never restart the `agy` daemon during apply**: it may host the active Remote Control session, so the reload hook only prints the restart command.

## Gotchas

- **Stay in user space**: never use `sudo`, system units, or `loginctl enable-linger` unasked; note if requested availability exceeds logged-in sessions.
- **Handle missed or timed-out runs explicitly**: choose skip vs coalesce deliberately and reconcile current state before re-running mutations.

## Documentation

- [systemd timers](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html) · [Apple scheduled jobs](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html)
