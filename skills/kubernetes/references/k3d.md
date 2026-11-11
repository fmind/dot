---
name: k3d
description: "Create, budget, and tear down disposable local k3d clusters for runtime tests."
---

# Local k3d Clusters

Requires a running Docker engine ([docker](../../docker/SKILL.md)) and `mise use --pin k3d`; check `dot doctor --headroom` first and prefer offline manifest checks whenever possible.

1. **Create with a unique name and pinned k3s tag** (`--kubeconfig-switch-context=false` preserves default kubeconfig; `--timeout` bounds startup and rolls back failures):

   ```bash
   k3d cluster list
   k3d cluster create <task-cluster> --agents 1 --kubeconfig-switch-context=false --image rancher/k3s:<k3s-tag> --timeout 5m
   ```

   Pass `--context k3d-<task-cluster>` on subsequent commands.

1. **Tear down only task-created clusters** (a failed create never authorizes deleting a pre-existing cluster sharing that name):

   ```bash
   k3d cluster stop <task-cluster>
   k3d cluster delete <task-cluster>
   ```

## Documentation

- [k3d](https://k3d.io/) · [releases](https://github.com/k3d-io/k3d/releases)
