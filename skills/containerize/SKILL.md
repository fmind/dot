---
name: containerize
description: Build a minimal non-root OCI image for a uv-managed Python app with a pinned multi-stage Dockerfile, then scan, sign, and attest it. Use when containerizing Python.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/containerize
  created: "2026-07-04"
  updated: "2026-09-06"
---

# Containerize a Python Application

Build a reproducible uv-managed Python image locally, verify it, and publish only within the user's authorized registry scope. [cloud-run](../cloud-run/SKILL.md) deploys it, [trivy](../trivy/SKILL.md) scans it, and [cosign](../cosign/SKILL.md) owns provenance.

## Workflow

1. **Adopt the templates**: copy [Dockerfile](references/Dockerfile) and [.dockerignore](references/.dockerignore). Replace `<slug>` with the installed Python console script and verify both image digests before use.
1. **Build locally**: emit a Docker archive so the first build and scan require no registry mutation.

   ```bash
   mkdir -p tmp
   docker buildx build --output type=docker,dest=tmp/image.tar .
   ```

1. **Wire the gate** into `mise.toml`; `check:image` scans the exact archive produced by `build:image`.

   ```toml
   [tasks."build:image"]
   description = "Build the Python OCI image locally"
   run = "mkdir -p tmp && docker buildx build --output type=docker,dest=tmp/image.tar ."

   [tasks."check:image"]
   description = "Scan the local OCI image"
   depends = ["build:image"]
   run = "trivy --config trivy.yaml image --input tmp/image.tar"
   ```

1. **Exercise the container**: load it with `docker load --input tmp/image.tar`, then run the reported local reference with `docker run --rm -p 8080:8080 -e PORT=8080 <local-reference>`.
1. **Publish when authorized**: push a reviewed tag with `docker buildx build --push --tag "$IMAGE_REPOSITORY:$TAG" --metadata-file tmp/image-metadata.json .`. Parse `containerimage.digest` from that file, require `sha256:` plus 64 lowercase hex characters, and record `$IMAGE_REPOSITORY@$DIGEST`.
1. **Verify the immutable result**: scan the recorded digest, generate a CycloneDX SBOM, sign it, pin the expected certificate identity and issuer during verification, and attest the SBOM per [trivy](../trivy/SKILL.md) and [cosign](../cosign/SKILL.md).

## Gotchas

- **Lock fidelity**: `uv sync --frozen` makes a stale or absent `uv.lock` fail the build; do not resolve dependencies inside the image build.
- **Non-root runtime**: the template runs as numeric UID/GID 10001 and copies only the locked virtual environment from the build stage. Write temporary data outside the application directory or mount an explicit writable path.
- **Pinned bases**: both Python and uv use multi-architecture manifest digests. Refresh versions and digests together with [upgrade-tools](../upgrade-tools/SKILL.md).
- **Small context**: keep virtual environments, caches, logs, local databases, Git state, and plaintext environment files out through [.dockerignore](references/.dockerignore).
- **Digests over tags**: scans, signatures, attestations, deployment, and rollback all use the same immutable digest reference.
- **Registry writes**: pushes, signatures, and attestations require explicit authority; local build and scan do not grant it.

## Documentation

- [Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/) · [uv Docker guide](https://docs.astral.sh/uv/guides/integration/docker/)
- Companion skills: [python-stack](../python-stack/SKILL.md), [cloud-run](../cloud-run/SKILL.md), [trivy](../trivy/SKILL.md), [cosign](../cosign/SKILL.md), [github-actions](../github-actions/SKILL.md), and [secure](../secure/SKILL.md).
