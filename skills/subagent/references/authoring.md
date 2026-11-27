# Authoring Zero-Hallucination Reviewer Supagents

Static reviewer `supagents` load with clean context (`excludeDefaultComponents: true`, `inheritCustomizations: false`) and **no progressive disclosure**: the full compiled body runs on turn 1 across every host.

## Core Design Laws

1. **One Discipline = One Supagent**: Split distinct surfaces (`mlops` vs `agents`, `cli` vs `api`, `sre` vs `cicd`, `human` vs `frontend`, `terraform` vs `architecture`) into single-purpose roles. Where one role spans sibling surfaces (`visuals`), surface-gate every rule.
1. **Self-Contained, Pragmatic Rules (Zero Name-Dropping)**: Never write `"Distills <Book / Standard>"`—translate primary docs into explicit checks (`Invariant + Why -> Flag <Observable Defect Conditions> -> Evidence`), forbidding unwritten rules. Scale to surface and risk so enterprise ceremony (KMS/HSM, multi-region HA, compliance) never misfires on scripts or prototypes.
1. **Three-Tier Independence**:
   - _Workstation (`dot/`, `AGENTS.md`, `skills/`)_: owns personal defaults and builder tools (`uv`, `ruff`, `dprint`, `Zensical`, `Cloud Run`).
   - _Global `fmind-review-*` (`dot_agents/supagents/`)_: encodes **tool- and stack-independent best practices**, security, YAGNI, and anti-slop craft. Never hardcode personal dotfiles (`~/.agents/DESIGN.md`), workstation linters (`dprint`, `vale`, `jactionlint`), or host tools (`search_web`).
   - _Project Overrides & Personas_: local `AGENTS.md`/`DESIGN.md`/`SECURITY.md` and `<org>-review-*` override defaults and may declare optional project `Priorities` (reviewers ignore `Priorities` and stay strictly single-lens—only the coordinator balances trade-offs; project docs never weaken read-only/security bounds, suppress `P0`/`P1`, or alter `Output Contract`). Keep stakeholder personas (`<org>-persona-{executive,developer,beginner,operator}`) project-local (`extends: _reviewer`) with domain exclusions.
1. **2-Tier Least Privilege, Frugal Routing & Fail-Closed Contract**: Hard-block shell, MCPs (`inheritMcp: false`), workspace inheritance (`inheritCustomizations: false`), edits, and delegation; coordinators pre-capture gates, manifests, and renders into `$render_dir`. Split partials into `_reviewer.md` (air-gapped) and `_reviewer_web.md` (`factcheck` only; `AGY.model: flash` routes in-session reviewers to `Gemini 4 Hydrogen (High)` per [cross-harness-agents](../../agent-harnesses/references/cross-harness-agents.md#permission-limits)). Enforce secret redaction, fail-closed `BLOCK` on unreadable targets, SSRF/privacy bounds, and bans on remote images, `manage_task` `send_input`/`kill`, and non-caller messaging inside `Output Contract`.

## Grounded Research Workflow

Use **authoritative primary sources only** (official docs, IETF/W3C/WCAG/OWASP/NIST/SPDX specs, peer-reviewed papers—no SEO blogs):

1. **Model-delta filter**: drop textbook basics; keep non-obvious failure modes, silent traps, edge cases, and pass/fail thresholds (pair defects caught by strict linters with a conditional `Do Not Flag` cue when clean linter logs are supplied).
1. **URL-free compiled prompts**: verify against primary docs during authoring; never inline URLs, HTML tags, or `## Sources` walls.

## Canonical 4-Block Blueprint (`~35`–`75` Lines, `< 7,000` Chars)

Use [templates/reviewer.md](../templates/reviewer.md) as a **standalone single-file starter** for repos without partials. In partial-based repos, omit frontmatter overrides (`description` `40`–`190` chars; use `_reviewer_web` on live-web fact-checking only):

```yaml
---
extends: _reviewer
name: org-review-role
description: Audit <domain> for <specific defects, contracts, and edge cases>.
---
```

Author four blocks before inherited `## Output Contract` (`SUMMARY: [<surface/scale>] <risk, outcome>`):

1. **Role & Surface/Scale Gate (`1` paragraph)**: Scope artifacts, skeptical stance, and upfront surface/scale classification.
1. **`## Audit Rubric` (`5`–`7` rules, ~40–55w each)**: Short _why_ + `Flag ...` thresholds; no echoed `Verify ...`, `CAPS`/`MUST`, or `!`.
1. **`## Do Not Flag` (`2`–`3` bullets)**: Conditional linter cue, scale exemptions, and exclusions (name sibling IDs only for high-collision pairs like `agents`↔`security`, `code`↔`simplicity`).
1. **`**Calibration**:` (`1` line)**: `P0`/`P1`/`P2` thresholds aligned to the canonical [balancing](balancing.md#canonical-severity-scale) scale (omit nits), mapping every cited defect class to `## Audit Rubric` rules.

## Pre-Delivery Meta-Audit

Build, clean, and check per [SKILL.md](../SKILL.md#author-compile--run) (or [gotchas](../SKILL.md#gotchas) in `fmind/dot`), audit with `fmind-review-supagent`, and calibrate per [calibration](calibration.md).
