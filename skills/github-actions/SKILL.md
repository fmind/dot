---
name: github-actions
description: Configure GitHub Actions for Python CI, PyPI Trusted Publishing, and signed Dockerfile images, with mise, actionlint, and zizmor. Use when adding or fixing Python workflows.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/github-actions
  created: "2026-07-04"
  updated: "2026-09-06"
---

# GitHub Actions for Python

CI runs the canonical [mise](../mise/SKILL.md) `all` task so it stays aligned with local [lefthook](../lefthook/SKILL.md) hooks; CD publishes Python distributions or Dockerfile images from version tags with short-lived OIDC credentials.

## Workflow

1. **CI**: copy [ci.yml](references/ci.yml) to `.github/workflows/ci.yml`; it runs `mise run all`, asserts an empty porcelain status so drift fails the build, and fetches 100 commits to match the `check:leaks` bound.
1. **Security**: copy [security.yml](references/security.yml) to `.github/workflows/security.yml`: a scheduled full-history [gitleaks](../gitleaks/SKILL.md) and [trivy](../trivy/SKILL.md) rescan where any finding fails the job.
1. **CD**: copy [cd.yml](references/cd.yml) to `.github/workflows/cd.yml`; enable `ENABLE_DEPLOY_PYPI`, `ENABLE_DEPLOY_CONTAINER`, or both. Configure the `pypi` environment and matching PyPI Trusted Publisher before enabling package publication. The image path expects the [containerize](../containerize/SKILL.md) Dockerfile, `trivy.yaml`, and `trivy` plus `cosign` in `mise.toml`.
1. **Lint the workflows**: pin `actionlint`, `shellcheck`, and `zizmor` in `mise.toml` `[tools]`, and expose `check:actions`:

   ```toml
   [tasks."check:actions"]
   description = "Lint and audit GitHub Actions workflows (actionlint + zizmor)"
   run = ["actionlint", "zizmor --offline .github/workflows/"]
   ```

1. **Verify locally**: run `mise run all`; when unrelated changes make a write-formatting gate unsafe, use an isolated working-tree copy containing the candidate edits or run `mise run check` and `mise run test` (see [mise](../mise/SKILL.md)).

## Principles

- **One gate**: CI runs `mise run all`, the same tasks the hooks call plus the production build.
- **Pinned project tools**: `jdx/mise-action` installs the `mise.toml` toolchain; commit `mise.lock` for stable caches and disable caches in release jobs.
- **Isolated publishing**: build distributions without OIDC, transfer only `dist/`, then grant `id-token: write` to the PyPI job. `pypa/gh-action-pypi-publish` performs Trusted Publishing and creates PyPI attestations.
- **Least privilege**: top-level `contents: read`; grant `id-token: write` only to publishers and `packages: write` only to the GHCR job.
- **Immutable images**: validate and scan the published Buildx digest, generate its CycloneDX SBOM, then sign, verify, attest, and verify the attestation with [trivy](../trivy/SKILL.md) and [cosign](../cosign/SKILL.md).
- **Immutable action refs**: use the full 40-character commit SHA plus the release as a trailing comment, such as `actions/checkout@<sha> # v7.0.1`; let Dependabot propose reviewed updates.

## Gotchas

- **Injection and cache poisoning**: `${{ ... }}` expands in `run:` before the shell runs, even inside comments; pass expression values through `env:` or action inputs and follow the `template-injection` and `cache-poisoning` fixes in [zizmor](../zizmor/SKILL.md).
- **Trusted Publisher identity**: PyPI must match the GitHub owner, repository, workflow filename, and optional `pypi` environment exactly; no API token is needed.
- **Separate security cadence**: full-history scans need `fetch-depth: 0` and minutes of runtime; keep them in the scheduled workflow with a job timeout.
- **Registry identity**: GHCR rejects uppercase repository paths, while the cosign certificate retains the GitHub workflow identity; lowercase only the image repository.
- **SHA comments drift**: when changing an action SHA manually, verify the release tag resolves to that exact commit and update its trailing comment in the same change.

## Documentation

- [GitHub Actions](https://docs.github.com/actions) · [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/) · [PyPA publish action](https://github.com/pypa/gh-action-pypi-publish) · [Docker build-push action](https://github.com/docker/build-push-action)
- Companion skills: [python-stack](../python-stack/SKILL.md), [zizmor](../zizmor/SKILL.md), [trivy](../trivy/SKILL.md), [containerize](../containerize/SKILL.md), [cosign](../cosign/SKILL.md), and [secure](../secure/SKILL.md).
