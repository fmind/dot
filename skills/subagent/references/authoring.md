# Authoring Zero-Hallucination Reviewer Supagents

Static reviewer `supagents` run with clean context (`excludeDefaultComponents: true`, `omitClaudeMd: true`) and **no progressive disclosure**: the full compiled body loads on turn 1 across every host.

## Core Design Laws

1. **One Discipline = One Supagent (Zero Progressive Disclosure)**: Split distinct disciplines or artifact surfaces (e.g., `mlops` vs `agents`, `cli` vs `api`, `sre` vs `cicd`, `human` vs `design`, `terraform` vs `architecture`) into single-responsibility supagents so coordinators fan out only matching roles.
1. **Self-Contained Operational Rules (Zero Standard Name-Dropping)**: Never write `"Distills <Book / Standard / Rules #1–#4>"` in prompt prose—naming external books without stating the check invites parametric hallucination. Translate standards at authoring time into explicit checks (`Invariant + Why -> Observable Defect Conditions -> Required Evidence`), and forbid unwritten external rules.
1. **Three-Tier Independence (`dot/` vs Global Reviewers vs Customer Overrides)**:
   - _Workstation (`dot/`, `AGENTS.md`, `skills/`)_: owns personal preferences and builder tools (`uv`, `ruff`, `dprint`, `Zensical`, `Cloud Run`).
   - _Global `fmind-review-*` (`dot_agents/supagents/`)_: encodes **tool- and stack-independent domain best practices** plus universal security, YAGNI, root-cause rigor, and anti-slop craft. Never hardcode personal dotfiles (`~/.agents/DESIGN.md`) or single-vendor tool mandates inside global rubrics.
   - _Project / Customer Overrides_: local `AGENTS.md`, `DESIGN.md`, and `SECURITY.md` override style/stack/architectural defaults (never read-only/security bounds or `Output Contract`), and repo `<org>-review-*` supagents override global `fmind-review-*` roles.
1. **2-Tier Least Privilege, Zero Shell & Zero MCP**: Hard-block shell (`run_command`, `Bash`, `PowerShell`, `execute`, `shell`), all MCPs (including browser MCPs, which expose upload/eval/file-write), file-edit, and delegation across every tier; coordinators run deterministic gates and browser/PDF renders first. Split partials into `_reviewer.md` (air-gapped read-only for 33 roles) and `_reviewer_web.md` (sanitized `https://` lookup for `factcheck` only). Keep `CLAUDE.disallowedTools` bare-tool only (parameterized `Read(...)` strips `Read` in Claude 2.1.x—put path denies in `settings.json` `permissions.deny`), put OpenCode secret denies on `action: read` (`*.env.example` right after `*.env*`, plus relative `.ssh/*` forms; omit `grep` on `_reviewer_web`), and put AGY secret denies in `settings.json`/`config.json` (`read_file(<abs>)`). Because `agy` 1.5.x CLI binds only `read_file`/`search_web`/`finish` and Copilot lacks frontmatter path denies, pass explicit paths/diffs/renders and sandbox web-tier runs. Omit step caps and enforce secret redaction + SSRF/privacy rules in `Output Contract`.

## Parallel Grounded Research Workflow (Authoring Time)

Fan out parallel searches against **authoritative primary sources only**:

1. **Query canonical standards & vendor docs**: official Google, Microsoft, AWS, Anthropic/OpenAI, HashiCorp/OpenTofu/K8s/Docker docs, IETF/W3C/WCAG/OWASP/NIST/SLSA/SPDX/FinOps specs, and peer-reviewed papers (`arxiv.org`/`doi.org`). Reject SEO blogs and forum hearsay.
1. **Apply a strict model-delta filter**: discard textbook basics frontier models know; keep non-obvious failure modes, silent traps, boundary edge cases, and pass/fail thresholds.
1. **Verify live URLs**: confirm every cited URL resolves (`lychee`) and record the grounded `Rubric #N` plus version or verification date (`YYYY-MM-DD`).

## Canonical 5-Block Operational Blueprint (`40`–`80` Compiled Lines, `< 10,000` Chars)

Keep child sources free of frontmatter overrides (`extends: _reviewer` | `_reviewer_web`, `name`, `description` in `40`–`190` chars) and structure the Markdown body in five exact blocks before the inherited `## Output Contract`:

1. **Role & Surface/Scale Gate (`1` short paragraph)**: State the exact artifacts in scope, skeptical specialist stance, and any upfront classification step (e.g., public site vs private app, library vs service, exploratory script vs production pipeline) so scale-sensitive rules never misfire.
1. **`## Audit Rubric` (`5`–`8` numbered operational rules)**: Write each rule once with its _why_ (dropping `CAPS`/`MUST` shouting and comma-stuffed keyword clouds):
   - **Bold Invariant & Why**: the failure risk if violated.
   - **Observable Defect Conditions**: concrete anti-patterns, edge cases, and quantitative thresholds to inspect across files.
   - **Required Evidence**: exact `path:line`, symbol, metric, or render check needed before flagging.
1. **`## Do Not Flag` (`2`–`4` bullets)**: Formatter/linter trivia caught by deterministic gates, out-of-scope scale/surface cases, and explicit handoffs to sibling `*-review-*` roles.
1. **`**Calibration**:` (`1` unwrapped line)**: Concrete domain thresholds separating `P0` (catastrophic/exploit/corruption) from `P1` (reachable contract/correctness/craft blocker) and `P2` (material maintainability/perf gap).
1. **`## Sources` (`4`–`8` bullets)**: `- [<Primary Title>](https://...) (<version or YYYY-MM-DD>) — grounds Rubric #<N> (<topic>).`, collectively covering every `Rubric #1`–`#<N>`.

## Pre-Delivery Meta-Audit

Compile (`supagents build --strict --project && supagents clean --project && supagents check --strict --project`, or the `fmind/dot` build and contract-test steps in [SKILL.md](../SKILL.md#gotchas)), run `lychee` on `## Sources`, audit with `fmind-review-supagent`, and run seeded-defect + clean-control probes per [calibration](calibration.md).
