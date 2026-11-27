---
name: subagent
description: "Author, compile, calibrate, and run read-only adversarial reviewer subagents (supagents or host roles)."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/subagent
  created: "2026-09-09"
  updated: "2026-11-25"
---

# Adversarial Reviewer Subagents

Keep producers dynamic (built-in subagents + skills); encode quality gates as static, clean-context, read-only reviewer `supagents`—never same-session skills. Project `AGENTS.md`/`DESIGN.md`/`SECURITY.md` and `<org>-review-*` override defaults without weakening security or `Output Contract`; reviewers ignore `Priorities` and stay strictly single-lens while the coordinator arbitrates trade-offs.

## Reviewer Families

Active roles are injected by host subagent discovery (`/agents`). Each extends `_reviewer.md` (air-gapped) or `_reviewer_web.md` (`factcheck` only; host limits in [cross-harness-agents](../agent-harnesses/references/cross-harness-agents.md#permission-limits)) across five lenses:

- **Software & Languages**: spec/PRD, completeness, architecture, code, simplicity, Python, shell, tests, CLI, API.
- **Infra, Reliability, Security & FinOps**: Terraform/OpenTofu, containers, CI/CD, SRE, security, FinOps.
- **Data, ML & AI**: data/SQL, analytics/experiments, MLOps, LLM agents/RAG/MCP, Agent Skills, reviewer supagents.
- **Docs, Fact-Checking, Writing & Legal**: docs, live fact-checking, busy-reader prose (`human`), compliance.
- **Visuals, Frontend & Proposals**: visuals/decks/charts/diagrams, frontend/WCAG/CWV, commercial proposals/SOWs.

## Author, Compile & Run

1. **Author & verify** ([authoring](references/authoring.md), standalone single-file starter at [template](templates/reviewer.md)): follow the 4-block single-discipline blueprint (or `extends: _reviewer` in partial-based repos), compile and check (`supagents build --strict --project && supagents clean --project --no-input && supagents check --strict --project`), audit with `fmind-review-supagent`, and calibrate live per [calibration](references/calibration.md).
1. **Coordinator-as-critic loop**:
   - **Preflight & capture (`0` tokens)**: verify no repo-local `.agents/agents/fmind-review-*`, `.agents/agents.json`, or `.github/agents/fmind-review-*` shadows global roles (`dot context --check`); run linters/tests/scanners/renders first and write frozen diffs, file manifests, gate logs, `--help`, and PNG/PDF/DOM renders to a temp dir (`agy` flags in [headless-review](../agent-harnesses/references/headless-review/GUIDE.md)).
   - **Fan out with absolute paths**: invoke `1`–`2` targeted roles in parallel (up to `3` on whole-repo or cross-cutting work) covering applicable optional project `Priorities` and passing **absolute file paths**—include `AGENTS.md`/`DESIGN.md`/`SECURITY.md` paths only when project rules apply (clean-context `agy` reviewers strip CWD, default to `model: flash` → `Gemini 4 Hydrogen (High)` in-session, and bind `read_file` only; unreadable primary targets fail closed with `BLOCK`; pass `--model gemini-4-hydrogen-medium` on headless `agy --agent` calls). Isolate `fmind-review-factcheck` in `/var/tmp` holding sanitized extracts on secret-bearing repos.
   - **Triage & stop**: verify every `rule:`/`loc:`/`evidence:` and severity, arbitrate `P0`–`P1` findings per [balancing](references/balancing.md) (plus quick `P2`/`DELETIONS` in one pass), cap at `2` rounds, and stop once active `P0`–`P1` blockers reach `PASS` (never re-review for `P2` or `DELETIONS`).
1. **Ratchet recurring `P1`s**: when a reviewer flags the same `P1` defect pattern `>= 2` times across diffs/sessions, propose promoting it into a mechanical gate via [lesson-learned](../skillify/references/lesson-learned.md).

## Severity and Priority Balancing

`P0`–`P2` measures **lens-local defect severity** (`P0` severe/irreversible harm, `P1` material defect/contract break, `P2` non-blocking improvement; omit nits, no `P3`), while the coordinator arbitrates cross-lens `P1` collisions via optional project `Priorities` in `AGENTS.md` and logs overrides in a `Trade-Offs` table—see [balancing](references/balancing.md) for the canonical severity table, axis-to-lens map, and arbitration rules.

## Gotchas

- `agy` snapshots custom agents at startup—test edits in a fresh or headless session (`mise run test:supagents:live` in `fmind/dot`).
- In `fmind/dot`, global sources live in `dot_agents/supagents/`, follow the repo `AGENTS.md` supagents gate, keep discovery `< 2,000` tok, retire old roles in `.chezmoiremove`, and run `mise run apply`.

## Documentation

- [Authoring](references/authoring.md) · [Balancing](references/balancing.md) · [Calibration](references/calibration.md) · [Template](templates/reviewer.md) · [agent-supagents](https://github.com/fmind/agent-supagents) · Companions: [full-review](../full-review/SKILL.md), [humanize](../humanize/SKILL.md), [cross-harness-agents](../agent-harnesses/references/cross-harness-agents.md), [headless-review](../agent-harnesses/references/headless-review/GUIDE.md).
