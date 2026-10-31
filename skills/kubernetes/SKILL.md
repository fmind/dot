---
name: kubernetes
description: "Operate Kubernetes with kubectl, Helm, kustomize, kubeconform, and stern."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/kubernetes
  created: "2026-09-16"
  updated: "2026-10-31"
---

# Kubernetes Cluster and Workload Operations

Use `kubectl`, `helm`, `kustomize`, `kubeconform`, and `stern` for Kubernetes cluster inspection, manifest authoring, Helm releases, and log debugging. [docker](../docker/SKILL.md) manages container runtimes and [infra-as-code](../infra-as-code/SKILL.md) provisions managed cloud clusters.

The workstation installs none of these tools globally: declare the ones the project uses, including `k3d` for local clusters, in its `mise.toml` with `mise use --pin <tool>` per [mise](../mise/SKILL.md).

Confirm user authority for cluster mutations and spending, reusing existing authorization. Pin `--context` and `--namespace` (or Helm's `--kube-context`) after resolving the intended cluster.

## Workflow

1. **Verify active context and namespace**: inspect the current cluster context before running any command; never assume terminal defaults point to dev.

   ```bash
   kubectl config get-contexts
   kubectl --context <context> cluster-info
   ```

1. **Lint and validate manifests**: validate schemas against the target cluster's version (kubeconform defaults to `master` schemas) and scan for misconfigurations with [trivy](../code-security/references/trivy/GUIDE.md) and the project's `trivy.yaml` before applying manifests.

   ```bash
   kubeconform -strict -summary -kubernetes-version <cluster-version> <file-or-directory>
   trivy --config trivy.yaml config <file-or-directory>
   kustomize build <kustomization-dir> | kubeconform -strict -summary -kubernetes-version <cluster-version> -
   ```

1. **Use a local cluster only when needed**: read [k3d](references/k3d.md) before creating or deleting one; manifest checks often answer the question without it.

1. **Deploy declaratively**: apply configurations using Helm or Kustomize; preview changes before mutating cluster state.

   ```bash
   helm upgrade --install <release-name> <chart-path> --kube-context <context> --namespace <namespace> --dry-run=server --hide-secret
   kubectl --context <context> --namespace <namespace> diff -k <kustomization-dir>
   ```

   A diff exit status of 1 means differences; higher values are errors. Review the preview, then apply within the authorized scope; with Helm 4 add `--rollback-on-failure --timeout <duration>`, which replaces the deprecated `--atomic` (as `--force-replace` replaces `--force`). `kubectl diff` masks Secret data unless `--show-secrets` is passed, but ConfigMaps and rendered chart values are not masked; exclude sensitive values from captured output.

1. **Inspect workloads and bounded logs**: narrow to the relevant workload and time window. Use finite log reads for agents; reserve streaming `stern` for an explicitly interactive investigation. The line limit applies per pod/container, so keep the pod query narrow.

   ```bash
   stern <pod-query> --context <context> -n <namespace> --since 15m --tail 50 --no-follow
   kubectl --context <context> get pods,events -n <namespace>
   ```

## Gotchas

- **Pin the context explicitly**: omitted context flags use mutable kubeconfig defaults. Pass the selected context on each call; change the persistent current context only when that change is requested.
- **Keep Secret payloads out of logs**: avoid running unbounded `kubectl get secret -o yaml`; inspect metadata and key names (`kubectl describe secret <name>` shows sizes, not values) without printing raw base64 payloads to terminal logs.

## Task guides

<!-- guides:start -->

- [k3d](references/k3d.md): Create, budget, and tear down disposable local k3d clusters for runtime tests.

<!-- guides:end -->

## Documentation

- [Kubernetes Documentation](https://kubernetes.io/docs/) · [Helm Documentation](https://helm.sh/docs/)
- [Stern Log Tailer](https://github.com/stern/stern) · [kubeconform](https://github.com/yannh/kubeconform)
- Releases: [Kubernetes Releases](https://github.com/kubernetes/kubernetes/releases) · [Helm](https://github.com/helm/helm/releases)
- Companion skills: [docker](../docker/SKILL.md) (container runtimes), [infra-as-code](../infra-as-code/SKILL.md) (provisioning), [incident-response](../production-readiness/references/incident-response.md) (outages).
