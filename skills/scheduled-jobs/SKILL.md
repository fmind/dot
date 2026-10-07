---
name: scheduled-jobs
description: "Schedule and debug local jobs with systemd timers or macOS launchd."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/scheduled-jobs
  created: "2026-09-09"
  updated: "2026-10-07"
---

# Scheduled Jobs

Run an existing bounded command through the native user scheduler and prove its outcome. [python-script](../python-stack/references/python-script/GUIDE.md) owns program code, and [mise](../mise/SKILL.md) owns task commands.

## Workflow

1. **Prove one invocation**: run the authorized command with explicit arguments and the scheduler's minimal environment. Use an existing dry-run mode when exercising real effects is outside scope; dry-run success does not prove a real run.
1. **Choose the native owner**: use [Linux user timers](references/linux.md) or [macOS LaunchAgents](references/macos.md). Keep an existing project scheduler unless migration is requested. Harness-native agent schedules remain with the matching host skill.
1. **Make execution bounded**: use an absolute executable path, explicit working directory, locked dependencies, bounded I/O and runtime, and one writer lock for all entry points. Decide whether a missed occurrence is skipped, coalesced, or replayed; replay requires an idempotent operation.
1. **Prepare the configuration**: call the existing command directly, keep branching in tested Python, and validate the unit or plist. Store durable job definitions in their owning repository; do not insert secrets into configuration, command lines, or logs.
1. **Activate within scope**: reuse explicit authority for recurring effects and cost. If it is missing, present the validated definition and precise schedule for approval before enabling it; preparing a schedule does not authorize its future effects.
1. **Verify execution**: distinguish loaded configuration, next due time, process completion, and the actual application result. Inspect a real scheduler-triggered run; a manual invocation or enabled timer is only partial evidence.
1. **Stop and recover**: disable future triggers and separately account for any running process and uncertain external write. Resume only from current state; do not blindly replay a timed-out mutation.

## Gotchas

- **Document laptop missed-run behavior**: sleep, power-off, login state, timezone changes, and DST affect schedules. Choose and document the missed-run behavior instead of promising an always-on service.
- **Stay in user space**: do not enable system services or lingering merely to keep a laptop job alive; explain when the requested availability exceeds a user session.

## Documentation

- [systemd timers](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html) · [Apple scheduled jobs](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html)
