---
name: kubernetes
description: "Operate Kubernetes clusters with kubectl, Helm, k9s, kustomize, and stern."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/kubernetes
  created: "2026-09-16"
  updated: "2026-09-26"
---

# Kubernetes Cluster and Workload Operations

Use `kubectl`, `helm`, `k9s`, `kustomize`, and `stern` for Kubernetes cluster inspection, manifest authoring, Helm releases, and log debugging. [docker](../docker/SKILL.md) manages container runtimes and [infra-as-code](../infra-as-code/SKILL.md) provisions managed cloud clusters.

Local k3d clusters need an existing Docker-compatible engine and 20 GiB disk headroom. Confirm user authority for cluster mutations and spending, reusing existing authorization. Pin `--context` and `--namespace` (or Helm's `--kube-context`) after resolving the intended cluster.

## Workflow

1. **Verify active context and namespace**: inspect the current cluster context before running any command; never assume terminal defaults point to dev.

   ```bash
   kubectl config get-contexts
   kubectl --context <context> cluster-info
   ```

1. **Lint and validate manifests**: validate schemas and verify security practices prior to applying manifests.

   ```bash
   kubeconform -strict <file-or-directory>
   kube-linter lint <file-or-directory>
   kustomize build <kustomization-dir>
   ```

1. **Spin up local clusters only when needed**: inspect `k3d cluster list`, confirm the resource budget, and choose a unique task-owned name before creation. Prefer manifest checks when they can answer the question; stop task clusters promptly after runtime tests.

   ```bash
   k3d cluster create <task-cluster> --agents 1 --kubeconfig-switch-context=false
   ```

1. **Deploy declaratively**: apply configurations using Helm or Kustomize; preview changes before mutating cluster state.

   ```bash
   helm upgrade --install <release-name> <chart-path> --kube-context <context> --namespace <namespace> --dry-run=server --hide-secret
   kubectl --context <context> --namespace <namespace> diff -k <kustomization-dir>
   ```

   A diff exit status of 1 means differences; higher values are errors. Review the preview, then apply within the authorized scope. Diffs may contain Secret values; exclude secrets from captured output.

1. **Inspect workloads and bounded logs**: narrow to the relevant workload and time window. Use finite log reads for agents; reserve `k9s` and streaming `stern` for an explicitly interactive investigation. The line limit applies per pod/container, so keep the pod query narrow.

   ```bash
   stern <pod-query> --context <context> -n <namespace> --since 15m --tail 50 --no-follow
   kubectl --context <context> get pods,events -n <namespace>
   ```

1. **Teardown task clusters**: stop or delete only the disposable cluster whose successful creation was recorded for this task. A failed create does not authorize deleting a pre-existing cluster with that name.

   ```bash
   k3d cluster stop <task-cluster>
   # Or delete:
   k3d cluster delete <task-cluster>
   ```

## Gotchas

- **Context changes**: omitted context flags use mutable kubeconfig defaults. Pass the selected context on each call; change the persistent current context only when that change is requested.
- **Off-by-default local clusters**: local k3d nodes consume significant CPU and RAM inside Docker or Colima; stop clusters when inactive.
- **Secret redaction**: avoid running unbounded `kubectl get secret -o yaml`; inspect metadata and annotate keys without printing raw base64 payloads to terminal logs.

## Documentation

- [Kubernetes Documentation](https://kubernetes.io/docs/) · [Helm Documentation](https://helm.sh/docs/)
- [k9s Terminal UI](https://k9scli.io/) · [Stern Log Tailer](https://github.com/stern/stern)
- Releases: [Kubernetes Releases](https://github.com/kubernetes/kubernetes/releases)
- Companion skills: [docker](../docker/SKILL.md) (container runtimes), [infra-as-code](../infra-as-code/SKILL.md) (provisioning), [incident-response](../incident-response/SKILL.md) (outages).
