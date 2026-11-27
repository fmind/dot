---
name: kubernetes
description: "Operate Kubernetes: kubectl, Helm, kustomize, kubeconform, stern."
---

# Kubernetes Cluster and Workload Operations

Inspect clusters, validate manifests, deploy Helm/Kustomize releases, and read bounded logs with `kubectl`, `helm`, `kustomize`, `kubeconform`, and `stern` ([docker](../docker/GUIDE.md) owns container runtimes; [infra-as-code](../../../infra-as-code/SKILL.md) owns cloud cluster provisioning).

None of these tools (or `k3d`) are installed globally: pin required ones in the project's `mise.toml` via `mise use --pin <tool>` ([mise](../../../mise/SKILL.md)). Confirm authority before mutating clusters or incurring spend, and pass `--context` and `--namespace` (`--kube-context` in Helm) explicitly on every call.

## Workflow

1. **Confirm context and cluster**: never assume default kubeconfig points to dev (`kubectl config get-contexts`, `kubectl --context <context> cluster-info`).
1. **Validate manifests offline**: check target-version schemas (`kubeconform` defaults to `master`) and scan with [trivy](../../../code-security/references/trivy/GUIDE.md) before applying (prefer offline validation over [k3d](references/k3d.md) when sufficient):

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

## Manifest Defaults

- **Pod Security `restricted`**: set `runAsNonRoot: true`, `allowPrivilegeEscalation: false`, `capabilities.drop: ["ALL"]`, `seccompProfile.type: RuntimeDefault`, `readOnlyRootFilesystem: true`, and `automountServiceAccountToken: false` (mount emptyDir for writable scratch).
- **Probes & graceful drain**: separate `readinessProbe`, `livenessProbe`, and `startupProbe`, and add a `lifecycle.preStop` drain delay with `terminationGracePeriodSeconds` exceeding drain + in-flight request timeouts.
- **Resources**: declare CPU and memory `requests` plus memory and `ephemeral-storage` `limits` (omit CPU limits unless strict throttling is required).
- **Secrets & RBAC**: keep plaintext `Secret` YAML out of Git (use External Secrets, SOPS, or KMS) and scope permissions with namespace `RoleBinding` instead of `ClusterRoleBinding`.

## Gotchas

- **Never mutate persistent kubeconfig context** unless explicitly asked; pass `--context` per command.
- **Never dump raw Secret values**: inspect keys/sizes via `kubectl describe secret <name>` instead of `kubectl get secret -o yaml`.

## References

- [k3d](references/k3d.md): Create, budget, and tear down disposable local k3d clusters for runtime tests.

## Documentation

- [Kubernetes](https://kubernetes.io/docs/) · [Helm](https://helm.sh/docs/) · [Stern](https://github.com/stern/stern) · [kubeconform](https://github.com/yannh/kubeconform) · [Kubernetes releases](https://github.com/kubernetes/kubernetes/releases) · [Helm releases](https://github.com/helm/helm/releases)
- Companion skills: [docker](../docker/GUIDE.md), [infra-as-code](../../../infra-as-code/SKILL.md).
