---
name: containers
description: "Run Docker, Compose, Colima; build, scan, sign Python images; operate Kubernetes (kubectl, Helm, kustomize, k3d)."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/containers
  created: "2026-11-21"
  updated: "2026-11-25"
---

# Containers & Kubernetes

Build, scan, sign, and run container images across Docker, Compose, and Colima, and operate Kubernetes clusters via `kubectl`, Helm, kustomize, kubeconform, stern, and local `k3d`. Audit manifests and Dockerfiles with `fmind-review-containers` and `fmind-review-security` ([subagent](../subagent/SKILL.md)).

## Task guides

<!-- guides:start -->

- [containerize](references/containerize/GUIDE.md): Build, scan, sign, and verify Python container images with Trivy and Cosign.
- [docker](references/docker/GUIDE.md): Run Docker, Compose, and Colima runtimes; sign and clean up container artifacts.
- [kubernetes](references/kubernetes/GUIDE.md): Operate Kubernetes: kubectl, Helm, kustomize, kubeconform, stern.

<!-- guides:end -->

## Documentation

- Companions: [infra-as-code](../infra-as-code/SKILL.md), [gcloud](../gcloud/SKILL.md), [code-security](../code-security/SKILL.md), [mise](../mise/SKILL.md).
