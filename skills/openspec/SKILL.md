---
name: openspec
description: "Manage repo openspec/ specs and changes via openspec CLI: initialize repos, author proposals/delta specs/designs/tasks, validate strictly, review, and archive."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/openspec
  created: "2026-11-27"
  updated: "2026-11-27"
---

# OpenSpec

Keep living capability specs in `openspec/specs/` and active work in `openspec/changes/` so `AGENTS.md` holds only always-on invariants and verified tasks. Enabled by default on new repos unless opted out; retrofit active multi-feature repos on demand. Use OpenSpec for multi-file features, contract changes, and architecture work—apply small bug fixes directly and update `openspec/specs/` only when behavior changes. Keep cross-repo notes in [bf](../bf/SKILL.md) and standalone PRDs/ADRs in [docs](../docs/SKILL.md).

## Workflow

1. **Initialize a repo (default on new repos)**:
   - Pin standalone `github:Fission-AI/OpenSpec`, `OPENSPEC_TELEMETRY = "0"`, and `check:specs` in `mise.toml` ([tool versions](../mise/references/tool-versions.md)), then run `mise lock`.
   - Scaffold `openspec/` without upstream skills and copy [config.yaml](templates/config.yaml) to `openspec/config.yaml` with non-inferable repo constraints only:
     ```bash
     OPENSPEC_TELEMETRY=0 CI=1 openspec init --tools none --no-animation </dev/null
     ```
   - Collaborator opt-in: if contributors without `fmind/dot` need upstream prompts, run `openspec init --scope project --profile core --no-animation </dev/null` and vet per [vendor-skills](../agent-harnesses/references/vendor-skills.md).
1. **Propose & plan a change**:
   - Create a kebab-case change and load schema instructions (`proposal`, `specs`, `design`, `tasks`):
     ```bash
     openspec new change <change-id>
     openspec status --change <change-id> --json
     openspec instructions proposal --change <change-id> --json
     ```
   - Write `proposal.md` (problem, first slice, out of scope), delta specs under `specs/<cap>/spec.md` (`## ADDED|MODIFIED|REMOVED|RENAMED Requirements`, `### Requirement:`, `#### Scenario:`), `design.md` (boundaries, failure modes, rollback), and `tasks.md`. For pure refactor/tooling/doc changes, set `skip_specs: true` in `.openspec.yaml`.
   - Run `openspec validate <change-id> --type change --strict --no-interactive`, then audit non-trivial plans with `fmind-review-spec` and `fmind-review-architecture` ([subagent](../subagent/SKILL.md)).
1. **Implement & verify**:
   - Load `openspec instructions apply --change <change-id> --json`, execute slices, check off `- [x]` items, run `mise run all`, and verify against specs via `fmind-review-completeness` (plus domain reviewers on risky changes).
1. **Archive & finalize**:
   - Merge deltas and archive (`--skip-specs` only when no spec changed):
     ```bash
     openspec archive -y <change-id>
     ```
   - Replace any new capability's `TBD` `## Purpose`, run `dprint fmt`, and pass both strict gates:
     ```bash
     openspec validate --all --strict --no-interactive
     openspec validate --archived --strict --no-interactive
     ```

## Gotchas

- **`--archived` overrides `--all`**: `openspec validate --all --archived --strict` skips active specs/changes; run both commands separately in `check:specs`.
- **Use glibc Linux tarballs, not `-musl`**: upstream `-musl` binaries link `/lib/ld-musl-*` (Alpine) and fail on Debian/Ubuntu; select `openspec-linux-{arm64,x64}.tar.gz` and `openspec-darwin-arm64.tar.gz`.
- **Close stdin non-interactively**: `openspec init --tools none --no-animation` can hang on open non-TTY stdin; pass `</dev/null` and `CI=1`.
- **Edit new main specs after archive**: archiving a brand-new capability writes a `TBD` `## Purpose` that fails `--strict`, and later deltas never overwrite it.
- **Never use `--scope global`**: global installs bypass chezmoi in `~/.agents/skills/` and fail `dot context --check` with duplicates.
- **Exclude archives from link/prose checks**: exclude `openspec/changes/archive` in `lychee` and `vale` so historical deltas never fail CI when paths move.
- **Pair cleanly with opt-in `pytest-bdd`**: on BDD repos ([testing/bdd](../python/references/testing/references/bdd.md)), match slugs (`openspec/specs/<cap>/spec.md` ↔ `features/<cap>.feature`), keep contracts + 1–2 canonical scenarios here, and keep executable `Examples:`/`@wip`/`@sla` scenarios in Gherkin without duplicating tables.

## Documentation

- [OpenSpec documentation](https://openspec.dev/) · [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec)
- Companions: [docs](../docs/SKILL.md), [github/bootstrap](../github/references/bootstrap.md), [mise](../mise/SKILL.md), [agent-harnesses](../agent-harnesses/references/project-setup.md), [subagent](../subagent/SKILL.md), [bf](../bf/SKILL.md).
