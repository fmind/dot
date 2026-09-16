---
name: containerize
description: "Build Python container images; scan, sign, and verify digests and attestations with Trivy and Cosign."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/containerize
  created: "2026-07-04"
  updated: "2026-09-16"
---

# Containerize

Build a minimal non-root Python image and verify its immutable digest. Select signing guidance only when publication or verification requires it.

## Workflow

Read only the matching guide and its required resources. Use a known guide directly when shared prerequisites are not needed.

## Task guides

<!-- guides:start -->

- [cosign](references/cosign.md): Image signatures, identity verification, and attestations.
- [image-build](references/image-build/GUIDE.md): Build Python container images, check runtime behavior, and clean task-owned resources.

<!-- guides:end -->
