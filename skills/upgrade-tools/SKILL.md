---
name: upgrade-tools
description: "Upgrade tools and dependencies and align repository pins with the workstation baseline."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/upgrade-tools
  created: "2026-07-05"
  updated: "2026-09-16"
---

# Upgrade Tools

Refresh the workstation's latest-stable tool baseline and propagate its exact versions to consuming repositories, validating each adoption. The [playbook](references/playbook.md) owns the cross-repository procedure and ecosystem commands; [mise](../mise/SKILL.md) owns baseline selection and exact pins.

## Workflow

1. **Inventory the scope**: check `fmind/dot` and Git repositories under `~/fmind`, `~/fmind-ai`, and `~/mlops-courses` by default, following the playbook. A task explicitly restricted to one repository narrows writes; report remaining drift. Cross-repository propagation covers mise tools and necessary compatibility changes, not blanket application-dependency upgrades everywhere.
1. **Separate audit from upgrade**: a disk-space or version-reuse check compares current declarations, locks, backends and installed versions without resolving new releases or installing tools. Include restored project directories with mise/runtime files even when `.git` is missing; report recovery gaps and validation limits. Record floating selectors, duplicate installations and justified compatibility exceptions separately.
1. **Baseline**: `mise run check` and `mise run test` must be green in a repository before its first bump so regressions are attributable. Preserve dirty work through [git-worktree](../git-worktree/SKILL.md); report pre-existing failures separately.
1. **mise first**: refresh and validate the `fmind/dot` baseline, then align consuming repositories to its exact lock versions. Python follows `latest` in the baseline like other tools; every consuming repo records fixed mise versions. Propagate only required shared tools, keeping incompatible pins with evidence.
1. **Python dependencies next** decide whether the new toolchain builds and tests the project; follow the [playbook](references/playbook.md) for `pyproject.toml` and `uv.lock`, then validate.
1. **Infrastructure and images after that** (OpenTofu providers, container base images), which consume the language artifacts.
1. **CI and formatter config last** (GitHub Actions, dprint), the outermost layer and the least likely to cascade.
1. **Stop the failing repository's upgrade** and diagnose before advancing its next ecosystem. Keep its original working pins if adoption cannot be qualified; independent repositories can still progress. A failed baseline update cannot be propagated.
1. **Verify the final candidate**: run the repository gate; test hook wiring when it changed. `lefthook run pre-commit --all-files` can format and restage unrelated work, so exercise it only in an isolated candidate when the original tree is dirty.
1. **If commits were requested**, commit per ecosystem: `chore(deps): upgrade <ecosystem> to latest` with its lockfile, per [conventional-commit](../git-delivery/references/conventional-commit.md).
1. **Report and preview cleanup**: list each repository's adopted versions, retained exceptions, and gate results. Preview `mise prune --dry-run` after alignment, checking interpreter links and active processes before any separately authorized deletion; do not equate directory sizes with recoverable bytes.

## Gotchas

- **Fresh selection, immutable execution**: only `fmind/dot` defaults to `latest` mise requests; consuming repositories pin the exact validated versions. Execute other dependencies through their lockfile, full action SHA, or image digest.
- **Latest stable only**: no RCs, betas, or pre-releases. Document deliberate baseline exceptions; keep application dependency constraints distinct from fixed mise tool versions.
- **Lockfiles are the record**: retain `mise.lock`, `uv.lock`, and `.terraform.lock.hcl` when present. Match the baseline's tool identity, backend, options, and platform rather than copying version strings or the entire workstation lockfile blindly.
- **Majors are separate changes**: Python upgrades follow declared constraints and `uv lock --upgrade` can cross majors. Inspect the actual version diff and handle breaking upgrades as separate changes.
- **Held-back pins**: a pin kept below latest carries a comment saying why (a parser ABI, a broken upstream asset); re-pin it deliberately instead of letting a bump carry it forward silently.

## Documentation

- [mise upgrade](https://mise.jdx.dev/cli/upgrade.html)
- [uv: upgrading locked versions](https://docs.astral.sh/uv/concepts/projects/sync/#upgrading-locked-package-versions)
- [OpenTofu lock file](https://opentofu.org/docs/language/files/dependency-lock/) · [dprint config update](https://dprint.dev/cli/#update)
- Releases: [mise](https://github.com/jdx/mise/releases) · [uv](https://github.com/astral-sh/uv/releases) · [OpenTofu](https://github.com/opentofu/opentofu/releases) · [dprint](https://github.com/dprint/dprint/releases)
- Companion skills: [mise](../mise/SKILL.md) (tool pins and lock), [dependabot](../github-actions/references/dependabot.md) (automated bumps), [repository-maintenance](../repository-maintenance/SKILL.md) (the pass that calls this skill).
