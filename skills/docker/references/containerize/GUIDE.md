---
name: containerize
description: "Build, scan, sign, and verify Python container images with Trivy and Cosign."
---

# Containerize

Build a reproducible, minimal non-root uv-managed Python image locally, verify its immutable digest, and publish only within the user's authorized registry scope. [cloud-run](../../../cloud-run/SKILL.md) deploys it, [trivy](../../../code-security/references/trivy/GUIDE.md) scans it, and [cosign](../cosign.md) owns provenance; read it only when publication or verification requires signing.

## Workflow

1. **Budget and identify resources**: inspect free space on the workspace and Docker storage filesystems, the selected Docker context, `docker system df`, and `docker buildx ls`. Run `dot doctor --headroom` first, then confirm the projected peak (context, layers, archive export and extraction) stays within the [resource cleanup](../resource-cleanup.md) budget. Record task-owned names/IDs before creating resources; use a unique Compose project or resource label so concurrent work stays separate.
1. **Adopt the templates**: copy [Dockerfile](templates/Dockerfile) and [.dockerignore](templates/.dockerignore). Replace `<slug>` with the installed Python console script and verify both image digests before use.
1. **Build locally**: emit a Docker archive so the first build and scan require no registry mutation.

   ```bash
   mkdir -p tmp
   docker buildx build --output type=docker,dest=tmp/image.tar .
   ```

1. **Wire the gate** into `mise.toml`; `check:image` scans the exact archive produced by `build:image`.

   ```toml
   [tasks."build:image"]
   description = "Build the Python OCI image locally"
   run = ["mkdir -p tmp", "docker buildx build --output type=docker,dest=tmp/image.tar ."]

   [tasks."check:image"]
   description = "Scan the local OCI image"
   depends = ["build:image"]
   run = "trivy --config trivy.yaml image --skip-dirs '' --input tmp/image.tar"
   ```

1. **Exercise the container**: load it with `docker load --input tmp/image.tar`. For the Python web starter, supply required application settings through a reviewed local environment file, then run `docker run --rm -p 127.0.0.1:8080:8080 --env-file <runtime-env-file> -e HOST=0.0.0.0 -e PORT=8080 -e ENVIRONMENT=production <local-reference>` and request `/health` and `/ready`. For a CLI image, exercise its actual command and exit behavior instead of publishing a port.
1. **Publish when authorized**: push a reviewed tag with `docker buildx build --push --tag "$IMAGE_REPOSITORY:$TAG" --metadata-file tmp/image-metadata.json .`. Parse `containerimage.digest` from that file, require `sha256:` plus 64 lowercase hex characters, and record `$IMAGE_REPOSITORY@$DIGEST`.
1. **Verify the immutable result**: run the [cosign release sequence](../cosign.md#release-sequence) on the recorded digest; the [CD template](../../../github-actions/references/ci-cd/templates/cd.yml) implements it.
1. **Tear down temporary resources** on success and failure, preserving requested deliverables and useful failure evidence. Follow [resource cleanup](../resource-cleanup.md), verify only recorded task resources disappeared, and report any retained disk footprint and reason.

## Gotchas

- **Fail on lock drift with `--locked`**: `uv sync --locked` rejects a missing or stale `uv.lock`; `--frozen` skips freshness checks. The template uses `--locked` so manifest drift fails without rewriting the graph.
- **Install exported pins without re-resolving**: an image that installs `uv export` output with pip needs `--no-deps` when the project overrides an upstream cap (`override-dependencies`); otherwise pip re-resolves and rejects the forced version.
- **Run non-root with explicit writable paths**: the template runs as numeric UID/GID 10001 and copies only the locked virtual environment from the build stage, owned by root so the application cannot rewrite its own code. Write temporary data outside the application directory or mount an explicit writable path.
- **Copy sources the environment does not hold**: the runtime stage copies only `/app/.venv`. A project with `[tool.uv] package = false` (the [Django bootstrap](../../../python-web/references/django/references/bootstrap.md)) or root-level `templates/` and `static/` directories must also copy the application tree (root-owned) and set the server entrypoint, or keep assets inside `src/<package>/`.
- **Refresh pinned bases together**: both Python and uv use multi-architecture manifest digests. Refresh versions and digests together with [upgrade-tools](../../../upgrade-tools/SKILL.md).
- **Exclude local state from the context**: keep virtual environments, caches, logs, local databases, Git state, plaintext environment files, and generated `gha-creds-*.json` Workload Identity Federation credentials out through [.dockerignore](templates/.dockerignore). The Cloud Run authentication action creates its credential file before the Docker build; it must not enter a build layer.
- **Reuse shared build cache under budget**: `--rm` removes a container, not its image, exported archive or build cache. Shared builder cache has no reliable per-agent ownership; reuse it under a reviewed storage budget instead of pruning it at every task end.

## Documentation

- [Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/) · [uv Docker guide](https://docs.astral.sh/uv/guides/integration/docker/)
- [Resource cleanup](../resource-cleanup.md) · [Build cache garbage collection](https://docs.docker.com/build/cache/garbage-collection/)
- Releases: [Docker Engine](https://docs.docker.com/engine/release-notes/) · [uv changelog](https://github.com/astral-sh/uv/blob/main/CHANGELOG.md)
- Companion skills: [python-stack](../../../python-stack/references/foundation/GUIDE.md), [cloud-run](../../../cloud-run/SKILL.md), [trivy](../../../code-security/references/trivy/GUIDE.md), [github-actions](../../../github-actions/references/ci-cd/GUIDE.md), and [code-security](../../../code-security/references/code-review/GUIDE.md).
