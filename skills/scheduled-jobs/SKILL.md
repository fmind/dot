---
name: scheduled-jobs
description: "Schedule and debug local jobs with systemd timers or macOS launchd."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/scheduled-jobs
  created: "2026-09-09"
  updated: "2026-11-07"
---

# Scheduled Jobs

Run an existing bounded command through the native user scheduler and prove its outcome. [python-script](../python-stack/references/python-script/GUIDE.md) owns program code, and [mise](../mise/SKILL.md) owns task commands.

## Workflow

1. **Choose the native owner**: [Linux user timers](references/linux.md) or [macOS LaunchAgents](references/macos.md); keep an existing project scheduler unless migration is requested, and leave harness-native agent schedules to the host skill.
1. **Keep definitions in the owning repository**: call an existing bounded command by absolute path with locked dependencies and one writer lock; enable it only after the user approves its recurring effects and schedule.
1. **Prove a scheduler-triggered run**: a manual run, valid unit, or enabled timer is partial evidence; check the real triggered run and its application result.

## Owner conventions

- **Workstation units live in fmind/dot**: put them in `dot_config/systemd/user/`, enable timers through a managed `timers.target.wants` symlink, and add each unit's hash to `run_onchange_after_systemd-user-reload.sh.tmpl`, which runs `systemctl --user daemon-reload` on apply.
- **Never restart the agy daemon from apply**: it may host this remote-control session; the reload hook only prints the restart command.

## Gotchas

- **Stay in user space**: do not enable system services or lingering merely to keep a laptop job alive; explain when the requested availability exceeds a user session.
- **Never blindly replay a timed-out mutation**: decide whether a missed run is skipped or coalesced, and resume only from current state.

## Documentation

- [systemd timers](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html) · [Apple scheduled jobs](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html)
