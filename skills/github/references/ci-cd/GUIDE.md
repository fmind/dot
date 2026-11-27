---
name: ci-cd
description: "Wire Python CI, scheduled security scans, and OIDC PyPI/OCI CD."
---

# GitHub Actions for Python

CI runs [mise](../../../mise/SKILL.md) `all` to match [lefthook](../../../git-delivery/references/lefthook.md); CD publishes packages or OCI images from `v*` tags via OIDC ([PyPI & OCI CD](references/cd.md)).

## Workflow

1. **Add CI**: copy [ci.yml](templates/ci.yml) (`mise run all` + clean `git status --porcelain`).
1. **Add scheduled scans**: copy [security.yml](templates/security.yml) (`check:leaks:full` via [betterleaks](../../../code-security/references/betterleaks.md), `check:network`, online audit); add `trivy` + `check:scan` ([trivy](../../../code-security/references/trivy/GUIDE.md)) for containers, IaC, or non-`uv` locks.
1. **Add CD (optional)**: follow [PyPI & OCI CD](references/cd.md) for [cd.yml](templates/cd.yml), [image-platforms.py](templates/image-platforms.py), and `ENABLE_DEPLOY_*`.
1. **Wire linting & Dependabot**: copy [jactionlint.yaml](../../templates/jactionlint.yaml) and [dependabot.yml](../../templates/dependabot.yml), pin `jactionlint` + `shellcheck`, and wire `check:actions` ([jactionlint](../jactionlint.md)). When adding [setup-mise](templates/setup-mise/action.yml) or any composite action under `.github/actions/`, use `directories: ["/", "/.github/actions/**/*"]` ([dependabot](../dependabot.md)).
1. **Verify & review**: run `mise run all` ([dirty-tree rule](../../../mise/SKILL.md#gotchas)), then audit workflow/auth changes with `fmind-review-cicd` and `fmind-review-security`.

## Principles

- **Lock installs & least privilege**: one task per step; pass `install_args: --locked` on `jdx/mise-action` (`cache: true` in CI, `cache: false` in deploy) or use [setup-mise](templates/setup-mise/action.yml). Set top-level `permissions: {}` (grant minimal job scopes) and `UV_LOCKED: "1"`; avoid bare `uvx`.
- **Pin actions to 40-hex SHAs**: `<owner>/<repo>@<sha> # vX.Y.Z`; Dependabot patches CVEs and [upgrade-tools](../../../mise/references/upgrade-tools/GUIDE.md) bumps the rest.
- **Libraries & PR coverage**: test lower bounds with `UV_LOCKED=0 uv run --isolated --resolution lowest-direct --no-dev --with pytest ... pytest -q`; optional PR [diff-cover](../../../python/references/testing/GUIDE.md#workflow) uses `fetch-depth: 0` on `pull_request` only and guards `$GITHUB_STEP_SUMMARY` with `!cancelled()`.

## Gotchas

- **Injection & full-history scans**: bind `${{ ... }}` via `env:` ([jactionlint](../jactionlint.md)); keep `fetch-depth: 0` secret scans in scheduled `security.yml` with `timeout-minutes`.
- **AI inputs & untrusted PRs**: `env:` never stops prompt injection; default to read-only jobs, withhold secrets/`id-token: write` on untrusted PRs, audit write sinks with `fmind-review-cicd`, and prove findings locally ([code-security](../../../code-security/references/code-review/GUIDE.md)).
- **Agentic workflows (`gh-aw`)**: pin `gh extension install github/gh-aw --pin <tag>`, review `.github/workflows/*.lock.yml` as supply-chain artifacts (narrow `jactionlint` ignores to locks), start with `staged: true`, `max-turns`, and credit caps, and require authority before `gh aw run`, unstaged safe outputs, `--push`, or `--auto-merge-prs` ([gh-aw](https://github.com/github/gh-aw)).
- **Tag-calling composite actions**: under `sha_pinning_required`, nested `@v*` actions fail; call the CLI directly.

## References

- [PyPI & OCI CD](references/cd.md) · [Actions](https://docs.github.com/actions) · [Trusted Publishers](https://docs.pypi.org/trusted-publishers/) · [publish action](https://github.com/pypa/gh-action-pypi-publish) · [build-push](https://github.com/docker/build-push-action)
- Companions: [python/foundation](../../../python/references/foundation/GUIDE.md), [jactionlint](../jactionlint.md), [trivy](../../../code-security/references/trivy/GUIDE.md), [containerize](../../../containers/references/containerize/GUIDE.md).
