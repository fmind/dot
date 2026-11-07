---
name: disk-space
description: "Audit workstation disk headroom, cache growth and shared tool versions before large downloads or builds."
---

# Disk Space

Keep the workstation usable without deleting shared resources or historical evidence. Check live state; a previous healthy report does not establish current headroom. This is an on-demand audit, not an installed monitor or cleanup schedule.

## Workflow

1. **Measure the right filesystem**: `dot doctor --headroom` prints one line for the workspace, home, `/var/tmp`, and an explicit `TMPDIR`; it warns below 20 GiB free and exits 1 below 10 GiB disk or 1 GiB memory. Use it alone for a pre-flight check; plain `dot doctor` applies the same disk thresholds and points to `dot cache` and `dot prune`. On ChromeOS, report Linux capacity separately from host storage, and ask the owner to check ChromeOS Storage management when host headroom is unknown. A full auxiliary read-only mount is not a full Linux disk.
1. **Classify headroom**: use available bytes, not summed directory sizes. Below 20 GiB available is a warning and below 10 GiB is critical, whatever the disk size; defer large optional downloads or builds until their projected peak (download, extraction, image layers, archives, disposable checkouts) leaves 20 GiB free.
1. **Find growth with bounded reads**: measure one filesystem at a time (`du -x`) over cache, data, and workspace roots, and record missing paths and permission failures instead of calling them empty. Btrfs/APFS sharing and hardlinks mean directory totals are not reclaimable bytes.
1. **Inspect native owners independently**: run `dot cache` (it skips uninstalled providers and a stopped Docker engine, and still reports the others when one inspection fails), then `dot cache docker`, `dot cache hf`, or `dot cache uv` to drill into one provider. Inspect the Docker context before probes. Distinguish missing cache directories, missing CLIs, and unavailable daemons from real zero usage.
1. **Audit tool reuse without upgrading**: compare declarations, locks, backends, and installed versions per [upgrade-tools](../../upgrade-tools/SKILL.md); leave pins unchanged and install or resolve nothing.
1. **Preview maintenance**: `dot prune --dry-run`, `dot prune --aggressive --dry-run`, and `mise prune --dry-run` are previews; `dot prune` never removes installed mise versions. Mise's tracked configs can omit restored or unvisited projects, virtualenv interpreter links, and running processes, so a prune candidate is not proof that deletion is safe. Preserve knowledge-base data and backups; inspect only their sizes unless content review is authorized. `dot prune uv` fails after 10 seconds while any `uv run` process holds the cache, such as `bf-watch.service`; stop that service for the prune and restart it rather than passing `--force`.
1. **Report and act within scope**: give the date, available space, largest consumers, version drift, and the next concrete action; mark inaccessible areas and host capacity as unverified. An audit leaves data and pins unchanged. For authorized cleanup, recheck ownership, remove exact disposable targets with native tools, and remeasure without attributing concurrent changes to your cleanup.

## Prevention

- **Audit before large downloads**: run this audit before large local builds or model and dataset downloads. Use [scheduled-jobs](../../scheduled-jobs/SKILL.md) only when recurring checks are requested, and prefer an alert at 20 GiB available over automatic deletion.
- **Reuse shared caches**: reuse compatible shared mise installations and uv/browser caches, keep normal project environments isolated, and use the [docker](../../docker/SKILL.md) skill for Docker ownership and teardown.

## References

- [ChromeOS storage](https://support.google.com/chromebook/answer/1061547) · [mise pruning](https://mise.jdx.dev/cli/prune.html) · [uv caching](https://docs.astral.sh/uv/concepts/cache/) · [Docker storage inspection](https://docs.docker.com/reference/cli/docker/system/df/)
