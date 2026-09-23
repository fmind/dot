---
name: disk-space
description: "Audit workstation disk headroom, cache growth and shared tool versions before large downloads or builds."
---

# Disk Space

Keep this workstation usable without deleting shared resources or historical evidence. Check live state; a previous healthy report does not establish current headroom. This is an on-demand audit, not an installed monitor or cleanup schedule.

## Workflow

1. **Measure the right filesystem**: run `df -h / ~`, and `df -h <workspace>` for work stored elsewhere. On Linux use `findmnt` to distinguish writable local mounts, temporary filesystems and host shares. On ChromeOS, report Linux capacity separately from host storage; ask the owner to check ChromeOS Storage management when host headroom is unknown. Do not interpret a full auxiliary read-only mount as a full Linux disk.
1. **Classify headroom**: use available bytes rather than summed directory sizes. On this 100 GiB workstation, warn below 20 GiB available and treat below 10 GiB as critical; defer large optional downloads/builds until projected peak usage leaves 20 GiB free. Account for download, extraction, image layers, exported archives and disposable checkouts. These are operating thresholds, not filesystem quotas.
1. **Find growth with bounded reads**: on Linux start with `du -x -h --max-depth=1 ~/.cache ~/.local/share ~/fmind ~/fmind-ai ~/mlops-courses /var`, then drill into the largest categories. On macOS use `du -x -h -d 1` on the relevant home/cache/workspace paths. Record missing paths and permission failures instead of calling them empty. Do not scan file contents or traverse host shares to measure local usage. Btrfs/APFS sharing and hardlinks mean directory totals are not reclaimable-byte estimates.
1. **Inspect native owners independently**: use `dot cache --help` and provider-specific `dot cache docker`, `dot cache hf`, and `dot cache uv` so one missing provider does not hide the others. Inspect Docker context before probes; include `docker system df`, `docker buildx ls`, and selected-builder usage where available. Distinguish missing cache directories, missing CLIs and unavailable daemons from real zero usage. Check system logs and installed system/user timers without changing them.
1. **Audit tool reuse without upgrading**: follow the installed `mise` and `upgrade-tools` skills. Read `~/.local/share/chezmoi/dot_config/mise/config.toml.tmpl` together with its adjacent lockfile. Discover root, nested, hidden/environment and task tool declarations under `~/fmind`, `~/fmind-ai` and `~/mlops-courses`, plus dot itself. Include restored directories without `.git`; exclude vendored trees, archived snapshots and disposable candidates, reporting exclusions. Canonicalize symlinked roots to avoid duplicate counting.
1. **Compare declarations and actual reuse**: other projects should pin exact baseline versions, with matching backend/options/platform, and coherent `.python-version` files. Compare their lock resolutions and `mise ls --installed --json`; supplement discovery with `mise ls --all-sources --json`. Report floating selectors, different pins, backend differences, missing locks and documented exceptions separately. A newer project pin needs investigation, not an automatic downgrade; intentional compatibility matrices can retain other versions. Do not install or resolve new releases for this audit.
1. **Preview maintenance**: `dot prune all --dry-run` and `mise prune --dry-run` are previews. `dot prune mise` clears cache, not installed versions. Mise's tracked configs can omit restored/unvisited projects, virtualenv interpreter links and running processes; a prune candidate is not proof that deletion is safe. Preserve FKF bases' `records/`, `originals/` and `inputs/` and their backups; inspect only their sizes unless content review is required and authorized. Their `.fkf/` caches are disposable and rebuild on the next search.
1. **Report and act within scope**: give date, available space, largest consumers, version drift, current cleanup/monitoring coverage and the next concrete action. Mark inaccessible areas and host capacity as unverified. For an audit, leave data and pins unchanged. For authorized cleanup, recheck ownership/consumers, remove exact disposable targets with native tools and remeasure; do not attribute concurrent changes to your cleanup. Record a short dated result in the existing task note when saving findings is authorized.

## Prevention

- Run this audit weekly and before large local builds or model/dataset downloads. A skill does not run itself: use the installed `scheduled-jobs` skill only when recurring checks are requested. Prefer an alert at 20 GiB available before considering automatic deletion; make missed checks and failures visible.
- Agents clean up their own disposable resources at task end, including failure. Use the installed `containerize` skill for Docker ownership and teardown; never infer disposability from stopped state or run broad prune commands for one task. Retain shared base images, persistent volumes and requested deliverables.
- Reuse compatible shared mise installations and uv/browser caches; remove task-only environments, profiles, archives and scratch checkouts once no longer needed. Keep normal project environments isolated and retain failure evidence deliberately.

## Tools and references

Required: shell, `df`, `du`, `rg` and mise; Linux uses `findmnt`. Dot, Docker, Btrfs and systemd probes are conditional on availability. Global workflow skills live under `~/.agents/skills/`; if absent, report the missing owner and use native read-only help rather than silently installing tools.

- [ChromeOS storage](https://support.google.com/chromebook/answer/1061547) · [mise pruning](https://mise.jdx.dev/cli/prune.html) · [uv caching](https://docs.astral.sh/uv/concepts/cache/) · [Docker storage inspection](https://docs.docker.com/reference/cli/docker/system/df/)
