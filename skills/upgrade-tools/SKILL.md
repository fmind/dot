---
name: upgrade-tools
description: "Upgrade a repository's tools and dependencies to latest stable, one repository at a time."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/upgrade-tools
  created: "2026-07-05"
  updated: "2026-10-06"
---

# Upgrade Tools

Upgrade one repository's tools and dependencies to their latest stable releases, validating each ecosystem. Each repository owns its pins: never change one because the workstation or a sibling upgraded. The [playbook](references/playbook.md) owns the ecosystem commands; [mise](../mise/SKILL.md) owns exact pins.

## Workflow

1. **Scope to the requested repository**: upgrade only the repository the user named, by default the current one. Never bump other repositories because `fmind/dot` or a sibling changed; a multi-repository upgrade needs the user's explicit list, and each repository is then upgraded on its own merits with its own gate and report.
1. **Separate audit from upgrade**: a disk-space or version-reuse check compares current declarations, locks, backends and installed versions without resolving new releases or installing tools. Include restored project directories with mise/runtime files even when `.git` is missing; report recovery gaps and validation limits. Record floating selectors, duplicate installations and justified compatibility exceptions separately.
1. **Start from a green baseline**: `mise run check` and `mise run test` must be green in a repository before its first bump so regressions are attributable. Preserve dirty work through [git-worktree](../git-worktree/SKILL.md); report pre-existing failures separately.
1. **mise first**: in `fmind/dot` run `mise run upgrade`; elsewhere resolve the latest stable releases of the project's own tools and pin them exactly per the [tool version rules](../mise/references/tool-versions.md), keeping incompatible pins with evidence.
1. **Python dependencies next**: they decide whether the new toolchain builds and tests the project; follow the [playbook](references/playbook.md) for `pyproject.toml` and `uv.lock`, then validate.
1. **Infrastructure and images after that** (OpenTofu providers, container base images), which consume the language artifacts.
1. **CI and formatter config last** (GitHub Actions, dprint), the outermost layer and the least likely to cascade.
1. **Stop the failing repository's upgrade** and diagnose before advancing its next ecosystem. Keep its original working pins if the upgrade cannot be qualified.
1. **Verify the final candidate**: run the repository gate; test hook wiring when it changed. `lefthook run pre-commit --all-files` can format and restage unrelated work, so exercise it only in an isolated candidate when the original tree is dirty.
1. **Commit per ecosystem when requested**: use `chore(deps): upgrade <ecosystem> to latest` with its lockfile, per [conventional-commit](../git-delivery/references/conventional-commit.md).
1. **Report and preview cleanup**: list the adopted versions, retained exceptions, and gate results, then preview cleanup as in the [playbook](references/playbook.md); deleting installations needs separate authorization.

## Gotchas

- **Latest stable only**: no RCs, betas, or pre-releases. Document deliberate exceptions; keep application dependency constraints distinct from fixed mise tool versions.
- **Lockfiles are the record**: retain `mise.lock`, `uv.lock`, and `.terraform.lock.hcl` when present, and execute non-mise dependencies through their lockfile, full action SHA, or image digest; the [tool version rules](../mise/references/tool-versions.md) own mise tool identity, backend, options, and platform.
- **Majors are separate changes**: Python upgrades follow declared constraints and `uv lock --upgrade` can cross majors. Inspect the actual version diff and handle breaking upgrades as separate changes.
- **Justify every held-back pin**: a pin kept below latest carries a comment saying why (a parser ABI, a broken upstream asset); re-pin it deliberately instead of letting a bump carry it forward silently.

## Documentation

- [mise upgrade](https://mise.jdx.dev/cli/upgrade.html)
- [uv: upgrading locked versions](https://docs.astral.sh/uv/concepts/projects/sync/#upgrading-locked-package-versions)
- [OpenTofu lock file](https://opentofu.org/docs/language/files/dependency-lock/) · [dprint config update](https://dprint.dev/cli/#update)
- Releases: [mise](https://github.com/jdx/mise/releases) · [uv](https://github.com/astral-sh/uv/releases) · [OpenTofu](https://github.com/opentofu/opentofu/releases) · [dprint](https://github.com/dprint/dprint/releases)
- Companion skills: [mise](../mise/SKILL.md) (tool pins and lock), [dependabot](../github-actions/references/dependabot.md) (automated bumps), [repository-maintenance](../repository-maintenance/SKILL.md) (the pass that calls this skill).
