---
name: containerize
description: "Build, scan, sign, and verify Python container images with Trivy and Cosign."
---

# Containerize

Build minimal, reproducible, non-root `uv` Python images locally, verify `@sha256:` digests, and push only within authorized registry scope ([cloud-run](../../../cloud-run/SKILL.md) deploys, [trivy](../../../code-security/references/trivy/GUIDE.md) scans, [cosign](../cosign.md) signs).

## Workflow

1. **Check headroom and isolate names**: run `dot doctor --headroom`, inspect `docker context ls`, `docker system df`, and `docker buildx ls`, confirm peak usage stays within the [resource cleanup](../resource-cleanup.md) floor, and record unique task-owned names/IDs up front.
1. **Copy templates**: adopt [Dockerfile](templates/Dockerfile) and [.dockerignore](templates/.dockerignore), set `<slug>` to the console script, and verify base digests.
1. **Build a local archive** (zero registry writes):

   ```bash
   mkdir -p tmp
   docker buildx build --tag <slug>:local --output type=docker,dest=tmp/image.tar .
   ```

1. **Wire `mise.toml` tasks**:

   ```toml
   [tasks."build:image"]
   description = "Build the Python OCI image locally"
   run = ["mkdir -p tmp", "docker buildx build --tag <slug>:local --output type=docker,dest=tmp/image.tar ."]

   [tasks."check:image"]
   description = "Scan the local OCI image"
   depends = ["build:image"]
   run = "trivy --config trivy.yaml image --skip-dirs '' --input tmp/image.tar"
   ```

1. **Smoke-test the image**: `docker load --input tmp/image.tar`, then test `/health` and `/ready` via `docker run --rm -p 127.0.0.1:8080:8080 --env-file <runtime-env-file> -e HOST=0.0.0.0 -e PORT=8080 -e ENVIRONMENT=production <slug>:local` (or exercise CLI args/exit codes directly for CLI images).
1. **Push when authorized**: run `docker buildx build --push --tag "$IMAGE_REPOSITORY:$TAG" --metadata-file tmp/image-metadata.json .`, validate `containerimage.digest` (`^sha256:[0-9a-f]{64}$`), and record `$IMAGE_REPOSITORY@$DIGEST`.
1. **Sign and attest**: run the [cosign release sequence](../cosign.md#release-sequence) on `$IMAGE_REPOSITORY@$DIGEST` (automated in the [CD template](../../../github-actions/references/ci-cd/templates/cd.yml)).
1. **Clean up** task-created artifacts on success or failure per [resource cleanup](../resource-cleanup.md) and report any retained footprint.

## Gotchas

- **Use `uv sync --locked`, not `--frozen`**: `--locked` fails on stale `uv.lock`, whereas `--frozen` ignores `pyproject.toml` drift.
- **Pass `pip --no-deps` on `uv export` installs**: prevents pip from re-resolving and rejecting `override-dependencies` pins.
- **Keep `/app/.venv` root-owned under UID `10001:10001`**: prevents runtime self-modification; mount or use an external writable dir for temp files.
- **Copy source trees when unbundled**: projects with `[tool.uv] package = false` ([Django bootstrap](../../../python-web/references/django/references/bootstrap.md)) or root `templates/`/`static/` must also copy root-owned app sources into the runtime stage.
- **Update tags and multi-arch digests together** via [upgrade-tools](../../../upgrade-tools/SKILL.md).
- **Keep secrets and WIF files out of build context**: [.dockerignore](templates/.dockerignore) excludes `.venv`, caches, DBs, `.git`, `.env*`, and `gha-creds-*.json` (written by `google-github-actions/auth` before `docker build`).
- **Keep shared Buildx cache**: `--rm` deletes only the container; reuse shared builder cache within budget instead of pruning per run.

## Documentation

- [Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/) · [uv Docker guide](https://docs.astral.sh/uv/guides/integration/docker/) · [Resource cleanup](../resource-cleanup.md) · [Build cache GC](https://docs.docker.com/build/cache/garbage-collection/) · [Docker releases](https://docs.docker.com/engine/release-notes/) · [uv changelog](https://github.com/astral-sh/uv/blob/main/CHANGELOG.md)
- Companion skills: [python-stack](../../../python-stack/references/foundation/GUIDE.md), [cloud-run](../../../cloud-run/SKILL.md), [trivy](../../../code-security/references/trivy/GUIDE.md), [github-actions](../../../github-actions/references/ci-cd/GUIDE.md), [code-security](../../../code-security/references/code-review/GUIDE.md).
