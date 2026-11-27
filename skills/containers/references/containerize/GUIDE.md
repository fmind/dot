---
name: containerize
description: "Build, scan, sign, and verify Python container images with Trivy and Cosign."
---

# Containerize

Build reproducible, non-root `uv` Python images locally, verify `@sha256:` digests, and push only within authorized registry scope ([cloud-run](../../../gcloud/references/cloud-run/GUIDE.md) deploys, [trivy](../../../code-security/references/trivy/GUIDE.md) scans, [cosign](../docker/references/cosign.md) signs).

## Workflow

1. **Check headroom & isolate names**: run `dot doctor --headroom`, `docker context ls`, `docker system df`, and `docker buildx ls`; stay within the [resource cleanup](../docker/references/resource-cleanup.md) floor and record task-owned names/IDs.
1. **Copy templates**: adopt [Dockerfile](templates/Dockerfile), [.dockerignore](templates/.dockerignore), and [trivy.yaml](../../../code-security/references/trivy/templates/trivy.yaml) (set `TRIVY_CONFIG = "trivy.yaml"` in `mise.toml` `[env]` for `check:image`), set `<slug>`, and verify base digests. Add [compose.yaml](templates/compose.yaml) (loopback Postgres/pgvector) for local stateful deps.
1. **Build local archive & wire `mise.toml`** (zero registry writes):

   ```toml
   [tasks."build:image"]
   description = "Build the Python OCI image locally"
   run = ["mkdir -p tmp", "docker buildx build --tag <slug>:local --output type=docker,dest=tmp/image.tar ."]

   [tasks."check:image"]
   description = "Scan the local OCI image"
   depends = ["build:image"]
   run = "trivy --config trivy.yaml image --skip-dirs '' --input tmp/image.tar"
   ```

1. **Smoke-test**: `docker load --input tmp/image.tar`, then test `/health` and `/ready` under least privilege (`docker run --rm --cap-drop=ALL --security-opt=no-new-privileges -p 127.0.0.1:8080:8080 --env-file <env-file> -e HOST=0.0.0.0 -e PORT=8080 -e ENVIRONMENT=production <slug>:local`, or exercise CLI exit codes; add `--read-only` when no FS writes occur).
1. **Push when authorized**: always pass explicit `--platform` (`linux/amd64` or `linux/amd64,linux/arm64`) on `docker buildx build --platform linux/amd64 --push --tag "$IMAGE_REPOSITORY:$TAG" --metadata-file tmp/image-metadata.json .`, validate `containerimage.digest` (`^sha256:[0-9a-f]{64}$`), and record `$IMAGE_REPOSITORY@$DIGEST`.
1. **Sign, attest & clean up**: run the [cosign release sequence](../docker/references/cosign.md#release-sequence) on `$IMAGE_REPOSITORY@$DIGEST` (automated in [CD template](../../../github/references/ci-cd/templates/cd.yml)), then clean task-owned artifacts per [resource cleanup](../docker/references/resource-cleanup.md).

## Gotchas

- **Use `uv sync --locked`, not `--frozen`**: `--locked` catches stale `uv.lock`; `--frozen` ignores `pyproject.toml` drift.
- **Trim runtime surface**: pass `pip --no-deps` on `uv export` installs, uninstall `pip` in slim runtime stages once `uv` copies `.venv`, and keep `/app/.venv` root-owned under UID `10001:10001`.
- **Copy unbundled trees**: `[tool.uv] package = false` ([Django bootstrap](../../../python/references/django/references/bootstrap.md)) or root `templates/`/`static/` must copy root-owned app sources into the runtime stage.
- **Compose `healthcheck:` vs platform probes**: use Compose `healthcheck:` only for local dependency readiness; define runtime `readinessProbe`/`livenessProbe` in Cloud Run or Kubernetes instead of image `HEALTHCHECK`.
- **Exclude secrets & WIF creds**: [.dockerignore](templates/.dockerignore) drops `.venv`, caches, DBs, `.git`, `.env*`, and `gha-creds-*.json`. Bump tags + digests together via [upgrade-tools](../../../mise/references/upgrade-tools/GUIDE.md) and reuse shared Buildx cache.

## Documentation

- [Multi-stage builds](https://docs.docker.com/build/building/multi-stage/) · [uv Docker](https://docs.astral.sh/uv/guides/integration/docker/) · [Docker releases](https://docs.docker.com/engine/release-notes/)
- Companions: [python/foundation](../../../python/references/foundation/GUIDE.md), [cloud-run](../../../gcloud/references/cloud-run/GUIDE.md), [trivy](../../../code-security/references/trivy/GUIDE.md), [github/ci-cd](../../../github/references/ci-cd/GUIDE.md).
