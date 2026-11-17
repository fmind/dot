# Authoring Zero-Hallucination Reviewer Supagents

Static reviewer `supagents` execute with clean context (`excludeDefaultComponents: true`, `omitClaudeMd: true`) and **no progressive disclosure**: unlike skills (`SKILL.md` -> `references/`), the entire compiled body loads on turn 1 across every host. Every design rule below follows from that constraint.

## Core Design Laws

1. **One Discipline = One Supagent (Zero Progressive Disclosure)**: If a reviewer must explain two distinct disciplines or artifact surfaces (e.g., `mlops` vs `agents`, `cli` vs `api`, `sre` vs `cicd`, `human` prose vs `design` layout, `terraform` HCL vs `arch` cloud design), split them into two single-responsibility supagents and let the coordinator fan out only matching roles.
1. **Self-Contained Operational Rules (Zero Standard Name-Dropping)**: Never write `"Distills <Book / Standard / Rules #1–#4>"` in prompt prose. Naming external books without stating the exact check invites parametric hallucination and dogmatic nitpicking. Translate external standards at authoring time into explicit operational checks (`Invariant + Why -> Observable Defect Conditions -> Required Evidence`), and forbid enforcing unwritten external rules.
1. **Three-Tier Independence (`dot/` vs Global Reviewers vs Customer Overrides)**:
   - _Workstation (`dot/`, `AGENTS.md`, `skills/`)_: owns personal preferences and builder tools (`uv`, `ruff`, `dprint`, `Zensical`, `Cloud Run`).
   - _Global `fmind-review-*` (`dot_agents/supagents/`)_: encodes **tool-independent, stack-independent domain best practices** plus universal security, YAGNI, root-cause rigor, and anti-slop craft. Never hardcode personal dotfiles (`~/.agents/DESIGN.md`) or single-vendor tool mandates inside global rubrics.
   - _Project / Customer Overrides_: local `AGENTS.md`, `DESIGN.md`, and `SECURITY.md` override style/stack/architectural defaults (never read-only/security boundaries or `Output Contract`), and repo-local `<org>-review-*` supagents take precedence over global `fmind-review-*` roles when present.
1. **Autonomous Read + Sanitized Web, Zero Step Caps**: Grant unrestricted file read/glob/grep/LSP and sanitized `https://` primary-source web lookup with **no turn/step limits** and **no brittle path denylists** in `_reviewer.md`, while blocking `Write`, `Edit`, `Shell`, `Task`/`Agent`, and `MCP`. Enforce secret value redaction in `evidence:` and SSRF/privacy query rules in `Output Contract`.

## Parallel Grounded Research Workflow (Authoring Time)

Before drafting or refreshing a supagent rubric, fan out parallel web searches against **authoritative primary sources only**:

1. **Query canonical engineering bodies & vendor docs**: official Google (Engineering Practices, SRE, Cloud Architecture, SAIF, `web.dev`, Search Central), Microsoft (Azure Architecture Center, Cloud Design Patterns, Engineering Playbook), AWS (Builders' Library, Well-Architected), Anthropic/OpenAI engineering research, HashiCorp/OpenTofu/Kubernetes/Docker docs, IETF RFCs, W3C/WCAG, OWASP, NIST, SLSA, SPDX, FinOps Foundation, and peer-reviewed papers (`arxiv.org`/`doi.org`). Reject SEO blogs, Medium summaries, and forum hearsay.
1. **Apply a strict model-delta filter**: discard textbook definitions and syntax trivia frontier models already know. Keep only non-obvious failure modes, silent correctness traps, boundary edge cases, and concrete pass/fail thresholds.
1. **Verify live URLs**: confirm every cited primary URL resolves cleanly (`lychee` online check) and record what specific `Rubric #N` rule it grounds plus its version or verification date (`YYYY-MM-DD`).

## Canonical 5-Block Operational Blueprint (`40`–`80` Compiled Lines, `< 10,000` Chars)

Keep child sources free of frontmatter overrides (`extends: _reviewer`, `name`, `description` in `40`–`190` chars) and structure the Markdown body in five exact blocks before the inherited `## Output Contract`:

1. **Role & Surface/Scale Gate (`1` short paragraph)**: State the exact artifacts in scope, skeptical specialist stance, and any upfront classification step (e.g., public site vs private app, library vs service, exploratory script vs production pipeline) so scale-sensitive rules never misfire.
1. **`## Audit Rubric` (`5`–`8` numbered operational rules)**: Write each rule once with its _why_ (dropping `CAPS`/`MUST` shouting and comma-stuffed keyword clouds):
   - **Bold Invariant & Why**: the failure risk if violated.
   - **Observable Defect Conditions**: concrete anti-patterns, edge cases, and quantitative thresholds to inspect across files.
   - **Required Evidence**: exact `path:line`, symbol, metric, or render check needed before flagging.
1. **`## Do Not Flag` (`2`–`4` bullets)**: Formatter/linter trivia caught by deterministic gates, out-of-scope scale/surface cases, and explicit handoffs to sibling `*-review-*` roles.
1. **`**Calibration**:` (`1`–`2` lines)**: Concrete domain thresholds separating `P0` (catastrophic/exploit/corruption) from `P1` (reachable contract/correctness/craft blocker) and `P2` (material maintainability/perf gap).
1. **`## Sources` (`4`–`8` bullets)**: `- [<Primary Title>](https://...) (<version or YYYY-MM-DD>) — grounds Rubric #<N> (<topic>).`

## Pre-Delivery Meta-Audit

Compile (`supagents build --strict --project && supagents check --strict --project`, or `mise run format:supagents && mise run check:supagents` in `fmind/dot`), run `lychee` on `## Sources`, audit the new definition with `fmind-review-supagent`, and run seeded-defect + clean-control probes per [calibration](calibration.md).
