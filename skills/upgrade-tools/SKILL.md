---
name: upgrade-tools
description: "Upgrade one repo's mise tools, uv deps, Actions, and images to latest stable."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/upgrade-tools
  created: "2026-07-05"
  updated: "2026-11-11"
---

# Upgrade Tools

Upgrade a single repository's tools and dependencies to latest stable releases in dependency order, gating each layer ([playbook](references/playbook.md) owns commands; [mise](../mise/SKILL.md) owns pin rules).

## Workflow

1. **Scope to one repository** (default `.`): never bump another repo unless the user gives an explicit list, canonicalizing paths/worktrees and qualifying each independently.
1. **Separate read-only audits from upgrades**: disk/drift audits inspect declarations, locks, backends, and installed versions (including `.git`-less restored folders) without resolving or installing anything.
1. **Require a green baseline**: pass `mise run check` and `mise run test` before bumping (isolate dirty trees via [git-worktree](../git-delivery/references/git-worktree/GUIDE.md); stop and report if baseline is red).
1. **Upgrade in layer order**, stopping to diagnose on any failure and restoring prior pins if unqualified:
   - **mise**: `mise run upgrade` (or `mise run lock:tool TOOL...`) in `fmind/dot`; exact stable pins per [tool-versions.md](../mise/references/tool-versions.md) elsewhere.
   - **Python**: `pyproject.toml` and `uv.lock` per [playbook.md](references/playbook.md).
   - **Infra & images**: OpenTofu providers and OCI base/fixture digests.
   - **CI & formatters**: GitHub Actions SHAs and `dprint` plugins.
1. **Verify the final candidate**: pass the full gate and runtime smoke checks (`lefthook run pre-commit --all-files` only in an isolated snapshot if the source tree is dirty).
1. **Commit per ecosystem on request**: `chore(deps): upgrade <ecosystem> to latest` with its lockfile (split `mise run upgrade` commits by lockfile) per [commit messages](../git-delivery/SKILL.md#commit-messages).
1. **Report and preview cleanup**: list old → new versions, held exceptions, gate results, and dry-run prune previews ([playbook.md](references/playbook.md)); deleting installs requires separate authority.

## Gotchas

- **Stable releases only**: skip RCs, betas, and pre-releases; keep `pyproject.toml` ranges distinct from exact `mise.toml` pins.
- **Keep lockfiles authoritative**: commit `mise.lock`, `uv.lock`, and `.terraform.lock.hcl`, and pin Actions by 40-hex SHA and images by `@sha256:` digest.
- **Isolate breaking majors**: `uv lock --upgrade` can cross majors within open constraints; review lock diffs and split breaking migrations.
- **Document held pins**: keep inline comments explaining every below-latest hold (ABI limits, broken upstream assets) and re-verify on each pass.
- **Check release notes for behavior shifts**: e.g. `betterleaks` 1.10 ignoring `.betterleaks.toml` without `--config` or `--unsafe-auto-load-config` ([betterleaks](../code-security/references/betterleaks.md)).
- **Check upstream READMEs for in-place successors**: `isArchived` and `mise registry` miss unarchived handoffs (`actionlint` → `jactionlint`, `gitleaks` → `betterleaks`).

## Documentation

- [mise upgrade](https://mise.jdx.dev/cli/upgrade.html) · [uv upgrading](https://docs.astral.sh/uv/concepts/projects/sync/#upgrading-locked-package-versions) · [OpenTofu lockfile](https://opentofu.org/docs/language/files/dependency-lock/) · [dprint update](https://dprint.dev/config/#updating-plugins-via-cli)
- Releases: [mise](https://github.com/jdx/mise/releases) · [uv](https://github.com/astral-sh/uv/releases) · [OpenTofu](https://github.com/opentofu/opentofu/releases) · [dprint](https://github.com/dprint/dprint/releases)
- Companion skills: [mise](../mise/SKILL.md), [dependabot](../github-actions/references/dependabot.md), [full-review](../full-review/SKILL.md).
