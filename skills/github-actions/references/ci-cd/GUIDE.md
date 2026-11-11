---
name: ci-cd
description: "GitHub Actions CI/CD setup, workflow validation, and publication."
---

# GitHub Actions for Python

CI runs [mise](../../../mise/SKILL.md) `all` so checks match local [lefthook](../lefthook.md) hooks; CD publishes Python packages or OCI images from `v*` tags via short-lived OIDC.

## Workflow

1. **Add CI**: copy [ci.yml](templates/ci.yml) to `.github/workflows/ci.yml` (`mise run all` plus a clean `git status --porcelain` check).
1. **Add scheduled scans**: copy [security.yml](templates/security.yml) to `.github/workflows/security.yml` for full-history [betterleaks](../../../code-security/references/betterleaks.md) (`check:leaks:full`) and `check:network` audits; when scanning containers, IaC, or non-`uv` lockfiles, pin `trivy` in `mise.toml` and wire `check:scan` + `trivy.yaml` into `check:network` per [trivy](../../../code-security/references/trivy/GUIDE.md).
1. **Add CD**: copy [cd.yml](templates/cd.yml) to `.github/workflows/cd.yml` and stdlib-only [image-platforms.py](templates/image-platforms.py) to `.github/scripts/image-platforms.py`; set `ENABLE_DEPLOY_PYPI`, `ENABLE_DEPLOY_CONTAINER`, or both after a read-only `validate` job passes `mise run all`. Configure the `pypi` environment and PyPI Trusted Publisher before package publishing; for images, include public Sigstore disclosure per [cosign](../../../docker/references/cosign.md) (or an approved private signer) and provide the [containerize](../../../docker/references/containerize/GUIDE.md) `Dockerfile`, `trivy.yaml`, and `trivy` + `cosign` in `mise.toml`.
1. **Wire workflow linting**: pin `jactionlint` and `shellcheck` in `mise.toml` `[tools]` and add `check:actions` to `check:local` `depends`:

   ```toml
   [tasks."check:actions"]
   description = "Validate GitHub Actions workflows and Dependabot config"
   run = "jactionlint --profile pedantic"
   ```

1. **Verify locally**: run `mise run all` (apply the [dirty-tree rule](../../../mise/SKILL.md#gotchas) when unrelated edits exist).

## Principles

- **Keep steps flat**: one direct command or `mise run <task>` per step, action outputs over CLI scraping, and non-trivial logic in versioned Python scripts rather than YAML shell blocks.
- **Pin tools and disable release caches**: `jdx/mise-action` installs `mise.toml` tools (`cache: true` in CI, `cache: false` in release/deploy jobs).
- **Separate build from publish**: build `dist/` without OIDC, upload only `dist/`, and grant `id-token: write` solely to the `pypa/gh-action-pypi-publish` job.
- **Verify candidate images before tag promotion**: push `:candidate-<sha>`, resolve every `PLATFORMS` child digest via `image-platforms.py`, run the [cosign release sequence](../../../docker/references/cosign.md#release-sequence) per child (signing the index once; default Trivy scans AMD64 only), then promote that index digest to release and `latest` tags via [Buildx imagetools](https://docs.docker.com/reference/cli/docker/buildx/imagetools/create/).
- **Pin actions to 40-hex SHAs**: write `<owner>/<repo>@<sha> # vX.Y.Z`; Dependabot updates vulnerable pins and [upgrade-tools](../../../upgrade-tools/SKILL.md) updates the rest.

## Gotchas

- **Prevent expression injection and cache poisoning**: `${{ ... }}` expands inside `run:` before shell parsing (even in comments); bind expressions via `env:` and follow [jactionlint](../jactionlint.md).
- **Match Trusted Publisher fields exactly**: GitHub owner, repo, workflow filename, and `pypi` environment must match PyPI verbatim.
- **Isolate full-history scans**: `fetch-depth: 0` scans belong in scheduled `security.yml` with a `timeout-minutes` cap.
- **Lowercase only the GHCR repo path**: cosign certificates preserve original GitHub workflow casing.
- **`env:` does not stop prompt injection**: treat issue, PR, log, and file inputs to AI steps as untrusted and audit every command, write, or publish sink before granting credentials.
- **Never run PR code with credentials**: keep secrets, `id-token: write`, and write permissions out of jobs checking out untrusted PR heads.
- **Prove AI-step findings locally**: reproduce in fixtures or authorized test workflows, never via PRs/comments on external repos ([code-security](../../../code-security/references/code-review/GUIDE.md)).
- **Avoid tag-calling composite actions under `sha_pinning_required`**: actions like `pre-commit/action` invoke nested `actions/cache@v4` by tag and fail; invoke tools directly (`pre-commit run --all-files --show-diff-on-failure`).
- **Keep SHA comments synced**: verify the tag resolves to the exact commit SHA whenever updating a pin manually.

## Documentation

- [GitHub Actions](https://docs.github.com/actions) · [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/) · [PyPA publish action](https://github.com/pypa/gh-action-pypi-publish) · [Docker build-push action](https://github.com/docker/build-push-action) · [changelog](https://github.blog/changelog/label/actions/)
- Companion skills: [python-stack](../../../python-stack/references/foundation/GUIDE.md), [jactionlint](../jactionlint.md), [trivy](../../../code-security/references/trivy/GUIDE.md), [containerize](../../../docker/references/containerize/GUIDE.md), [cosign](../../../docker/references/cosign.md), [code-security](../../../code-security/references/code-review/GUIDE.md).
