---
name: kubernetes
description: Operate Kubernetes clusters with kubectl, helm, k9s, kustomize, and stern. Use for cluster inspection, manifests, releases, and pod logs.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/kubernetes
  created: "2026-09-16"
  updated: "2026-09-16"
---

# Kubernetes Cluster and Workload Operations

Use `kubectl`, `helm`, `k9s`, `kustomize`, and `stern` for Kubernetes cluster inspection, manifest authoring, Helm releases, and log debugging. [docker](../docker/SKILL.md) manages container runtimes and [terraform](../terraform/SKILL.md) provisions managed cloud clusters.

## Workflow

1. **Verify active context and namespace**: inspect the current cluster context before running any command; never assume terminal defaults point to dev.

   ```bash
   kubectl config current-context
   kubectl cluster-info
   # Switch context or namespace if needed:
   kubectx
   kubens
   ```

1. **Lint and validate manifests**: validate schemas and verify security practices prior to applying manifests.

   ```bash
   kubeconform -strict <file-or-directory>
   kube-linter lint <file-or-directory>
   kustomize build <kustomization-dir>
   ```

1. **Spin up local clusters on demand**: create isolated local clusters with `k3d` or `kind` when testing locally, and stop them promptly when finished to conserve memory.

   ```bash
   k3d cluster create local --agents 1
   # Or using kind:
   kind create cluster --name local
   ```

1. **Deploy declaratively**: apply configurations using Helm or Kustomize; preview changes before mutating cluster state.

   ```bash
   helm upgrade --install <release-name> <chart-path> --namespace <namespace> --create-namespace
   kubectl apply -k <kustomization-dir> --dry-run=client
   ```

1. **Inspect workloads and tail logs**: monitor cluster state interactively with `k9s` or follow multi-pod logs with `stern`.

   ```bash
   k9s
   stern <pod-query> -n <namespace> --tail 50
   kubectl get pods,events -n <namespace>
   ```

1. **Teardown local clusters**: stop or delete ephemeral clusters after testing.

   ```bash
   k3d cluster stop local
   # Or delete:
   k3d cluster delete local
   ```

## Gotchas

- **Context hijacking**: commands run against `kubectl config current-context`; verify active context on every session before executing changes.
- **Off-by-default local clusters**: local k3d/kind nodes consume significant CPU and RAM inside Docker or Colima; stop clusters when inactive.
- **Secret redaction**: avoid running unbounded `kubectl get secret -o yaml`; inspect metadata and annotate keys without printing raw base64 payloads to terminal logs.

## Documentation

- [Kubernetes Documentation](https://kubernetes.io/docs/) · [Helm Documentation](https://helm.sh/docs/)
- [k9s Terminal UI](https://k9scli.io/) · [Stern Log Tailer](https://github.com/stern/stern)
- Releases: [Kubernetes Releases](https://github.com/kubernetes/kubernetes/releases)
- Companion skills: [docker](../docker/SKILL.md) (container runtimes), [terraform](../terraform/SKILL.md) (provisioning), [incident-response](../incident-response/SKILL.md) (outages).
