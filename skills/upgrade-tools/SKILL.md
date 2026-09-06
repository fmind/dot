---
name: upgrade-tools
description: Upgrade pinned tools and dependencies to latest stable one ecosystem at a time, validating mise, language, action, and formatter changes between bumps. Use when bumping versions.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/upgrade-tools
  created: "2026-07-05"
  updated: "2026-09-06"
---

# Upgrade Tools

Bump every pinned tool and dependency to its latest stable version, one ecosystem at a time, validating after each so a bad bump is caught immediately; the per-manifest commands live in the [playbook](references/playbook.md) and [mise](../mise/SKILL.md) owns the tool pins.

## Workflow

1. **Baseline**: `mise run check` and `mise run test` must be green before the first bump so regressions are attributable.
1. **mise first**: it provisions the toolchain every later step runs; bump and re-lock the pins per [mise](../mise/SKILL.md), then validate.
1. **Python dependencies next** decide whether the new toolchain builds and tests the project; follow the [playbook](references/playbook.md) for `pyproject.toml` and `uv.lock`, then validate.
1. **Infrastructure and images after that** (OpenTofu providers, container base images), which consume the language artifacts.
1. **CI and formatter config last** (GitHub Actions, dprint), the outermost layer and the least likely to cascade.
1. **Stop at the first failing ecosystem** and fix it before continuing; bumping the rest on top of a broken one turns a short upgrade into an afternoon of bisecting.
1. **Run the hooks once at the end**: `lefthook run pre-commit --all-files` and `lefthook run pre-push --all-files`.
1. **If commits were requested**, commit per ecosystem: `chore(deps): upgrade <ecosystem> to latest` with its lockfile, per [conventional-commit](../conventional-commit/SKILL.md).

## Gotchas

- **Fresh selection, immutable execution**: track the latest compatible stable release in manifests and update automation, but execute the reviewed result through a lockfile, full action SHA, or image digest. Mutable selectors belong at update time, not on every run.
- **Latest stable only**: no RCs, betas, or pre-releases; tools deliberately range-pinned pre-1.0 stay in their range.
- **Lockfiles are the record**: commit `mise.lock`, `uv.lock`, `.terraform.lock.hcl` when present; the manifest says "latest", the lockfile says which.
- **Majors are separate changes**: Python upgrades follow declared constraints and `uv lock --upgrade` can cross majors. Inspect the actual version diff and handle breaking upgrades as separate changes.
- **Held-back pins**: a pin kept below latest carries a comment saying why (a parser ABI, a broken upstream asset); re-pin it deliberately instead of letting a bump carry it forward silently.

## Documentation

- [mise upgrade](https://mise.jdx.dev/cli/upgrade.html)
- [uv: upgrading locked versions](https://docs.astral.sh/uv/concepts/projects/sync/#upgrading-locked-package-versions)
- [OpenTofu lock file](https://opentofu.org/docs/language/files/dependency-lock/) · [dprint config update](https://dprint.dev/cli/#update)
- Companion skills: [mise](../mise/SKILL.md) (tool pins and lock), [dependabot](../dependabot/SKILL.md) (automated bumps), [project-health](../project-health/SKILL.md) (the pass that calls this skill).
