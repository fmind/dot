# Authoring Zero-Hallucination Reviewer Supagents

Static reviewer `supagents` load with clean context (`excludeDefaultComponents: true`) and **no progressive disclosure**: the entire compiled body runs on turn 1 across every host.

## Core Design Laws

1. **One Discipline = One Supagent (Zero Progressive Disclosure)**: Split distinct disciplines or surfaces (e.g., `mlops` vs `agents`, `cli` vs `api`, `sre` vs `cicd`, `human` vs `frontend`, `terraform` vs `architecture`) into single-purpose supagents so coordinators invoke only matching roles.
1. **Self-Contained, Pragmatic Rules (Zero Name-Dropping)**: Never write `"Distills <Book / Standard>"`—translate primary docs into explicit checks (`Invariant + Why -> Observable Defect Conditions -> Evidence`), forbidding unwritten rules. Scale requirements to surface and risk so enterprise ceremony (KMS/CMK, multi-region HA, formal compliance) is never forced onto small scripts or personal/prototype repos.
1. **Three-Tier Independence (`dot/` vs Global vs Customer Overrides)**:
   - _Workstation (`dot/`, `AGENTS.md`, `skills/`)_: owns personal preferences and builder tools (`uv`, `ruff`, `dprint`, `Zensical`, `Cloud Run`).
   - _Global `fmind-review-*` (`dot_agents/supagents/`)_: encodes **tool- and stack-independent best practices**, security, YAGNI, root-cause rigor, and anti-slop craft. Never hardcode personal dotfiles (`~/.agents/DESIGN.md`) or single-vendor mandates.
   - _Project Overrides_: local `AGENTS.md`, `DESIGN.md`, and `SECURITY.md` override style/stack/architecture defaults (never read-only/security bounds or `Output Contract`); `<org>-review-*` overrides `fmind-review-*`.
1. **2-Tier Least Privilege, Zero Shell & Zero MCP**: Hard-block shell (`run_command`, `execute`, `shell`), all MCPs (including browser MCPs), file-edit, and delegation across every tier; coordinators pre-capture gates, manifests, and renders into `$render_dir`. Split partials into `_reviewer.md` (air-gapped read-only) and `_reviewer_web.md` (sanitized `https://` lookup, `factcheck` only). Follow [cross-harness permission limits](../../agent-harnesses/references/cross-harness-agents.md#permission-limits). Omit step caps and enforce secret redaction + SSRF/privacy in `Output Contract`.

## Grounded Research Workflow

Research against **authoritative primary sources only** (official vendor docs, IETF/W3C/WCAG/OWASP/NIST/SPDX specs, peer-reviewed papers—reject SEO blogs):

1. **Apply a model-delta filter**: drop textbook basics; keep non-obvious failure modes, silent traps, boundary edge cases, and pass/fail thresholds.
1. **Keep compiled prompts URL-free**: verify rules against primary docs during authoring, and never inline `## Sources` URL walls into compiled reviewer prompts.

## Canonical 4-Block Blueprint (`~35`–`75` Compiled Lines, `< 7,000` Chars)

Keep child sources free of frontmatter overrides (`extends: _reviewer` | `_reviewer_web`, `name`, `description` in `40`–`190` chars) and author four crisp blocks before inherited `## Output Contract`:

1. **Role & Surface/Scale Gate (`1` paragraph)**: State in-scope artifacts, skeptical stance, and upfront classification (public vs private site, library vs service, script vs production) so scale-sensitive rules never misfire.
1. **`## Audit Rubric` (~`5`–`8` numbered rules, ~40–55 words each)**: State each check once cleanly (short _why_ + concrete `Flag ...` conditions/thresholds; no echoed `Verify ...` restatements, `CAPS`/`MUST` shouting, or `!` marks).
1. **`## Do Not Flag` (~`2`–`4` bullets)**: Deterministic-gate trivia, out-of-scope scale/surface cases, and reciprocal handoffs to sibling roles.
1. **`**Calibration**:` (`1` unwrapped line)**: Domain thresholds separating `P0` (catastrophic/exploit/corruption), `P1` (contract/correctness/craft blocker), and `P2` (advisory maintainability/perf note).

## Pre-Delivery Meta-Audit

Compile (`supagents build --strict --project && supagents clean --project && supagents check --strict --project`, or `fmind/dot` steps in [SKILL.md](../SKILL.md#gotchas)), audit with `fmind-review-supagent`, and run seeded-defect + clean-control probes per [calibration](calibration.md).
