---
name: disk-space
description: "Audit disk headroom, cache growth, and shared tool versions before large builds or downloads."
---

# Disk Space

Run an on-demand live headroom audit without deleting shared state or historical records.

## Workflow

1. **Check filesystem headroom**: `dot doctor --headroom` checks workspace, `$HOME`, `/var/tmp`, and explicit `TMPDIR` in one line, warning below 20 GiB free and exiting 1 below 10 GiB disk or 1 GiB memory (`dot doctor` uses the same disk thresholds). Defer large optional builds or downloads unless projected peak usage leaves ≥20 GiB available (check available bytes, never summed directory sizes, and ignore full read-only auxiliary mounts).
1. **Locate growth safely**: run bounded single-filesystem `du -x` checks across cache, data, and workspace roots, recording missing or unreadable paths as unverified (CoW/hardlink sharing means `du` totals exceed reclaimable bytes).
1. **Inspect native caches**: run `docker system df` (check Docker context first), `hf cache ls`, and `du -sh "$(uv cache dir)"`, distinguishing uninstalled CLIs, stopped daemons, and missing directories from zero usage.
1. **Audit tool drift read-only**: compare declarations, locks, backends, and installed versions per [upgrade-tools](../../mise/references/upgrade-tools/GUIDE.md) without editing pins or installing.
1. **Preview cleanup**: run `mise prune --dry-run` (candidates can still back unvisited repos, venv symlinks, or running processes) and inspect native tool caches (`uv cache prune --dry-run`, `docker builder prune` previews) without removing installed versions, credentials, or sessions. Never touch knowledge-base data or backups; if `bf-watch.service`, `bf watch`, or another `uv run` holds the uv cache lock, stop and restart that process instead of passing `--force`.
1. **Report or clean within scope**: report date, free bytes, top consumers, version drift, unverified paths, and next actions; when cleanup is authorized, recheck ownership, remove exact disposable targets via native tools, and remeasure without claiming concurrent changes.

## Prevention

- **Check before heavy jobs**: audit before large builds, images, models, or datasets; use [scheduled-jobs](scheduled-jobs/GUIDE.md) only on request, preferring a 20 GiB alert over auto-deletion.
- **Share caches, isolate envs**: reuse mise installs and uv/browser caches, keep project `.venv`s isolated, and follow [docker](../../containers/references/docker/GUIDE.md) for container teardown.

## References

- [mise pruning](https://mise.jdx.dev/cli/prune.html) · [uv caching](https://docs.astral.sh/uv/concepts/cache/) · [Docker storage inspection](https://docs.docker.com/reference/cli/docker/system/df/)
