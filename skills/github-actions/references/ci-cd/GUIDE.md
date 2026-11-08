---
name: ci-cd
description: "GitHub Actions CI/CD setup, workflow validation, and publication."
---

# GitHub Actions for Python

CI runs the canonical [mise](../../../mise/SKILL.md) `all` task so it stays aligned with local [lefthook](../lefthook.md) hooks; CD publishes Python distributions or Dockerfile images from version tags with short-lived OIDC credentials.

## Workflow

1. **Add the CI workflow**: copy [ci.yml](templates/ci.yml) to `.github/workflows/ci.yml`; it runs `mise run all` and asserts an empty porcelain status so drift fails the build.
1. **Add the security workflow**: copy [security.yml](templates/security.yml) to `.github/workflows/security.yml`: a scheduled full-history [betterleaks](../../../code-security/references/betterleaks.md) and [trivy](../../../code-security/references/trivy/GUIDE.md) rescan where any finding fails the job. It calls `check:scan`, so first pin trivy in `mise.toml` and add the `check:scan` task and `trivy.yaml` from the trivy guide; the Python starter does not define them.
1. **Add the CD workflow**: copy [cd.yml](templates/cd.yml) to `.github/workflows/cd.yml` and [image-platforms.py](templates/image-platforms.py) to `.github/scripts/image-platforms.py`; enable `ENABLE_DEPLOY_PYPI`, `ENABLE_DEPLOY_CONTAINER`, or both. Commit the helper with the workflow; it uses only Python's standard library. A read-only job runs `mise run all` on the tagged revision and rejects generated drift before either publisher starts. Configure the `pypi` environment and matching PyPI Trusted Publisher before enabling package publication. Before enabling image publication, include public Sigstore identity/digest disclosure in the signing scope per [Cosign](../../../docker/references/cosign.md), or configure an approved private signing service. The image path expects the [containerize](../../../docker/references/containerize/GUIDE.md) Dockerfile, `trivy.yaml`, and `trivy` plus `cosign` in `mise.toml`.
1. **Lint the workflows**: pin `jactionlint` and `shellcheck` in `mise.toml` `[tools]`, expose `check:actions`, and add it to `check:local`'s `depends` so hooks and CI run it:

   ```toml
   [tasks."check:actions"]
   description = "Validate GitHub Actions workflows and Dependabot config"
   run = "jactionlint"
   ```

1. **Verify locally**: run `mise run all`; when the tree carries unrelated changes, apply the [dirty-tree rule](../../../mise/SKILL.md#gotchas).

## Principles

- **Keep steps simple**: one direct command or `mise run <task>` per step, named steps for scan, sign, and verification, and action outputs over parsed CLI output; keep branching and retries in maintained source, not YAML shell blobs.
- **Run one gate in CI**: CI runs `mise run all`, the same tasks the hooks call plus the production build.
- **Pin project tools**: `jdx/mise-action` installs the `mise.toml` toolchain; commit `mise.lock` for stable caches and disable caches in release jobs.
- **Isolate publishing from builds**: build distributions without OIDC, transfer only `dist/`, then grant `id-token: write` to the PyPI job. `pypa/gh-action-pypi-publish` performs Trusted Publishing and creates PyPI attestations.
- **Verify images before promoting tags**: push a candidate tag, resolve every requested platform's child digest from the Buildx index, and run the [cosign release sequence](../../../docker/references/cosign.md#release-sequence) per child (sign the index once). Only then promote that same index digest to the version and `latest` tags with [Buildx imagetools](https://docs.docker.com/reference/cli/docker/buildx/imagetools/create/), so a rejected candidate leaves consumer tags unchanged. Keep `PLATFORMS` as the shared build/validation declaration; Trivy's default scan covers only AMD64.
- **Pin actions to commit SHAs**: use the full 40-character commit SHA plus the release as a trailing comment, such as `actions/checkout@<sha> # v7.0.1`; Dependabot security updates bump a vulnerable pin and its comment, and [upgrade-tools](../../../upgrade-tools/SKILL.md) refreshes the rest.

## Gotchas

- **Guard against injection and cache poisoning**: `${{ ... }}` expands in `run:` before the shell runs, even inside comments; pass expression values through `env:` or action inputs and follow the `template-injection` and `cache-poisoning` fixes in [jactionlint](../jactionlint.md).
- **Trusted Publisher identity must match exactly**: PyPI must match the GitHub owner, repository, workflow filename, and optional `pypi` environment exactly; no API token is needed.
- **Schedule full-history scans separately**: full-history scans need `fetch-depth: 0` and minutes of runtime; keep them in the scheduled workflow with a job timeout.
- **Lowercase only the image repository**: GHCR rejects uppercase repository paths, while the cosign certificate retains the GitHub workflow identity; lowercase only the image repository.
- **`env:` stops shell injection, not prompt injection**: issue, PR, log, and file content passed to an AI step stays untrusted to the agent; trace its output to every shell command, API write, or publication it can reach before granting that step credentials.
- **Never run untrusted PR code in a credentialed job**: a trusted workflow file does not make the checked-out pull-request content trusted; keep secrets, `id-token: write`, and write tokens out of jobs that build or execute it.
- **Prove an AI-step finding with a fixture**: reproduce it in a local fixture or an authorized test workflow, never by opening a PR or comment on another repository; [code-security](../../../code-security/references/code-review/GUIDE.md) owns finding verification.
- **Run tools directly under SHA-pinning policy**: with `sha_pinning_required`, a composite action that calls another action by tag fails the job (`pre-commit/action` calls `actions/cache@v4`); run the tool itself, such as `pre-commit run --all-files --show-diff-on-failure`.
- **SHA comments drift**: when changing an action SHA manually, verify the release tag resolves to that exact commit and update its trailing comment in the same change.

## Documentation

- [GitHub Actions](https://docs.github.com/actions) · [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/) · [PyPA publish action](https://github.com/pypa/gh-action-pypi-publish) · [Docker build-push action](https://github.com/docker/build-push-action)
- Releases: [GitHub Actions changelog](https://github.blog/changelog/label/actions/)
- Companion skills: [python-stack](../../../python-stack/references/foundation/GUIDE.md), [jactionlint](../jactionlint.md), [trivy](../../../code-security/references/trivy/GUIDE.md), [containerize](../../../docker/references/containerize/GUIDE.md), [cosign](../../../docker/references/cosign.md), and [code-security](../../../code-security/references/code-review/GUIDE.md).
