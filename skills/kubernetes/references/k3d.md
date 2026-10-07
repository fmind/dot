---
name: k3d
description: "Create, budget, and tear down disposable local k3d clusters for runtime tests."
---

# Local k3d Clusters

Local k3d clusters need an existing Docker-compatible engine (see [docker](../../docker/SKILL.md)); run `dot doctor --headroom` before creating one. Prefer manifest checks when they can answer the question.

1. **Create only when needed**: inspect `k3d cluster list`, confirm the resource budget, and choose a unique task-owned name. Keep the current kubeconfig context unchanged and pass `--context k3d-<task-cluster>` afterwards.

   ```bash
   k3d cluster create <task-cluster> --agents 1 --kubeconfig-switch-context=false
   ```

1. **Tear down promptly**: after runtime tests, stop or delete only the disposable cluster whose successful creation was recorded for this task. A failed create does not authorize deleting a pre-existing cluster with that name.

   ```bash
   k3d cluster stop <task-cluster>
   # Or delete:
   k3d cluster delete <task-cluster>
   ```

## Documentation

- [k3d](https://k3d.io/) · Releases: [k3d](https://github.com/k3d-io/k3d/releases)
