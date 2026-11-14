---
name: kubernetes
description: "Operate Kubernetes with kubectl, Helm, kustomize, kubeconform, and stern."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/kubernetes
  created: "2026-09-16"
  updated: "2026-11-14"
---

# Kubernetes Cluster and Workload Operations

Inspect clusters, validate manifests, deploy Helm/Kustomize releases, and read bounded logs with `kubectl`, `helm`, `kustomize`, `kubeconform`, and `stern` ([docker](../docker/SKILL.md) owns container runtimes; [infra-as-code](../infra-as-code/SKILL.md) owns cloud cluster provisioning).

None of these tools (or `k3d`) are installed globally: pin required ones in the project's `mise.toml` via `mise use --pin <tool>` ([mise](../mise/SKILL.md)). Confirm authority before mutating clusters or incurring spend, and pass `--context` and `--namespace` (`--kube-context` in Helm) explicitly on every call.

## Workflow

1. **Confirm context and cluster**: never assume default kubeconfig points to dev (`kubectl config get-contexts`, `kubectl --context <context> cluster-info`).
1. **Validate manifests offline**: check target-version schemas (`kubeconform` defaults to `master`) and scan with [trivy](../code-security/references/trivy/GUIDE.md) before applying (prefer offline validation over [k3d](references/k3d.md) when sufficient):

   ```bash
   kubeconform -strict -summary -kubernetes-version <cluster-version> <file-or-directory>
   trivy --config trivy.yaml config <file-or-directory>
   kustomize build <kustomization-dir> | kubeconform -strict -summary -kubernetes-version <cluster-version> -
   ```

1. **Preview and deploy declaratively**:

   ```bash
   helm upgrade --install <release-name> <chart-path> --kube-context <context> --namespace <namespace> --dry-run=server --hide-secret
   kubectl --context <context> --namespace <namespace> diff -k <kustomization-dir>
   ```

   `kubectl diff` exits `1` on diffs and `>1` on errors; it masks `Secret` data (without `--show-secrets`) but not `ConfigMap`s or rendered values. On authorized Helm 4 applies, pass `--rollback-on-failure --timeout <duration>` (replaces deprecated `--atomic`; `--force-replace` replaces `--force`).

1. **Read bounded logs and events** (`--tail` applies per container; reserve streaming `stern` for interactive sessions; `kubectl --context <context> get events -n <namespace>` for cluster events):

   ```bash
   stern <pod-query> --context <context> -n <namespace> --since 15m --tail 50 --no-follow
   ```

## Gotchas

- **Never mutate persistent kubeconfig context** unless explicitly asked; pass `--context` per command.
- **Never dump raw Secret values**: inspect keys/sizes via `kubectl describe secret <name>` instead of `kubectl get secret -o yaml`.

## Task guides

<!-- guides:start -->

- [k3d](references/k3d.md): Create, budget, and tear down disposable local k3d clusters for runtime tests.

<!-- guides:end -->

## Documentation

- [Kubernetes](https://kubernetes.io/docs/) · [Helm](https://helm.sh/docs/) · [Stern](https://github.com/stern/stern) · [kubeconform](https://github.com/yannh/kubeconform) · [Kubernetes releases](https://github.com/kubernetes/kubernetes/releases) · [Helm releases](https://github.com/helm/helm/releases)
- Companion skills: [docker](../docker/SKILL.md), [infra-as-code](../infra-as-code/SKILL.md).
