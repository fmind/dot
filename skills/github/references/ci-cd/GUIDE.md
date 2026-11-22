---
name: ci-cd
description: "Wire Python CI, scheduled security scans, and OIDC PyPI/OCI CD."
---

# GitHub Actions for Python

CI runs [mise](../../../mise/SKILL.md) `all` to match local [lefthook](../lefthook.md) hooks; CD publishes Python packages or OCI images from `v*` tags via OIDC.

## Workflow

1. **Add CI**: copy [ci.yml](templates/ci.yml) to `.github/workflows/ci.yml` (`mise run all` + clean `git status --porcelain`).
1. **Add scheduled scans**: copy [security.yml](templates/security.yml) to `.github/workflows/security.yml` (`check:leaks:full` via [betterleaks](../../../code-security/references/betterleaks.md) + `check:network`). For containers, IaC, or non-`uv` locks, pin `trivy` and wire `check:scan` + `trivy.yaml` per [trivy](../../../code-security/references/trivy/GUIDE.md).
1. **Add CD**: copy [cd.yml](templates/cd.yml) and stdlib-only [image-platforms.py](templates/image-platforms.py) (`.github/scripts/`); set `ENABLE_DEPLOY_PYPI` and/or `ENABLE_DEPLOY_CONTAINER` after `validate` passes `mise run all`. Configure the `pypi` environment + PyPI Trusted Publisher for packages; for images, include Sigstore disclosure ([cosign](../../../containers/references/docker/references/cosign.md)), [containerize](../../../containers/references/containerize/GUIDE.md) `Dockerfile`, `trivy.yaml`, and `trivy` + `cosign` in `mise.toml`.
1. **Wire linting & Dependabot**: copy [jactionlint.yaml](../../templates/jactionlint.yaml) to `.github/jactionlint.yaml` and [dependabot.yml](../../templates/dependabot.yml) to `.github/dependabot.yml`, pin `jactionlint` + `shellcheck`, and add `check:actions` ([jactionlint](../jactionlint.md)) to `check:local` `depends`.
1. **Verify locally**: run `mise run all` (apply the [dirty-tree rule](../../../mise/SKILL.md#gotchas) when unrelated edits exist).

## Principles

- **Keep steps flat**: one command or `mise run <task>` per step; use action outputs over CLI scraping and Python scripts over YAML shell blocks.
- **Disable release caches**: `jdx/mise-action` sets `cache: true` in CI and `cache: false` in release/deploy jobs.
- **Separate build from publish**: build `dist/` without OIDC, upload `dist/`, and grant `id-token: write` solely to `pypa/gh-action-pypi-publish`, which signs single-subject PEP 740 `publish/v1` attestations (PyPI **Full Provenance**; never pre-create `*.publish.attestation` or split uploads).
- **Verify candidate images before promotion**: push `:candidate-<sha>`, resolve `PLATFORMS` child digests via `image-platforms.py`, run the [cosign release sequence](../../../containers/references/docker/references/cosign.md#release-sequence) per child (signing the index once; default Trivy scans AMD64 only), then promote that digest via [Buildx imagetools](https://docs.docker.com/reference/cli/docker/buildx/imagetools/create/).
- **Pin actions to 40-hex SHAs**: write `<owner>/<repo>@<sha> # vX.Y.Z`; Dependabot patches vulnerabilities and [upgrade-tools](../../../mise/references/upgrade-tools/GUIDE.md) updates the rest.

## Gotchas

- **Stop expression injection**: `${{ ... }}` expands in `run:` before shell parsing (even in comments); bind via `env:` per [jactionlint](../jactionlint.md).
- **Match Trusted Publisher fields verbatim**: owner, repo, workflow filename, and `pypi` environment.
- **Isolate `fetch-depth: 0` scans**: keep them in scheduled `security.yml` with `timeout-minutes`.
- **Lowercase only the GHCR repo path**: cosign certificates preserve workflow filename casing.
- **Treat AI inputs as untrusted and deny PR creds**: `env:` does not stop prompt injection—audit every write/publish sink; omit secrets, `id-token: write`, and write permissions when checking out untrusted PRs. Prove AI-step findings locally, never on external repos ([code-security](../../../code-security/references/code-review/GUIDE.md)).
- **Avoid tag-calling composite actions under `sha_pinning_required`**: e.g., `pre-commit/action` invokes nested `@v4` tags and fails; call `pre-commit run --all-files --show-diff-on-failure` directly. Keep `# vX.Y.Z` comments synced to exact SHAs.

## Documentation

- [Actions](https://docs.github.com/actions) · [Trusted Publishers](https://docs.pypi.org/trusted-publishers/) · [publish action](https://github.com/pypa/gh-action-pypi-publish) · [build-push](https://github.com/docker/build-push-action) · [changelog](https://github.blog/changelog/label/actions/)
- Companions: [python/foundation](../../../python/references/foundation/GUIDE.md), [jactionlint](../jactionlint.md), [trivy](../../../code-security/references/trivy/GUIDE.md), [containerize](../../../containers/references/containerize/GUIDE.md), [cosign](../../../containers/references/docker/references/cosign.md), [code-security](../../../code-security/references/code-review/GUIDE.md).
