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

Active roles are injected by host subagent discovery (`/agents`). Each extends `_reviewer.md` (air-gapped read-only) or `_reviewer_web.md` (`factcheck` only), with zero shell/MCP/edit/delegation tools across five lenses:

- **Software & Languages**: spec/PRD, completeness, architecture, code, simplicity, Python, shell, tests, CLI, API.
- **Infra, Reliability, Security & FinOps**: Terraform/OpenTofu, containers, CI/CD, SRE, security, FinOps.
- **Data, ML & AI**: data/SQL, analytics/experiments, MLOps, LLM agents/RAG/MCP, Agent Skills, reviewer supagents.
- **Docs, Fact-Checking, Writing & Legal**: docs, live fact-checking, busy-reader prose (`human`), compliance.
- **Visuals, Frontend & Proposals**: visuals/decks/charts, frontend/WCAG/CWV, commercial proposals/SOWs.

## Author, Compile & Run

1. **Author/refresh** ([authoring](references/authoring.md)): 1 discipline = 1 supagent (no `references/`), pragmatic risk-scaled model-delta rules (`~35`–`75` compiled lines, `< 7,000` chars; [template](templates/reviewer.md)), grounded in verified primary docs without inlining URL walls in compiled prompts. Build & check via `supagents build --strict --project && supagents clean --project && supagents check --strict --project`, then audit via `fmind-review-supagent` and [calibration](references/calibration.md).
1. **Coordinator-as-critic loop**: run linters/tests/scanners/renders first (`0` tokens); capture frozen diffs, manifests, gate logs, `vale --output=JSON`, `--help`, and PNG/PDF/DOM renders to a temp dir (`agy` flags in [headless-review](../agent-harnesses/references/headless-review/GUIDE.md)); fan out `1`–`5` roles in parallel covering applicable optional project `Priorities` (isolate `fmind-review-factcheck` on secret-bearing repos per [cross-harness-agents](../agent-harnesses/references/cross-harness-agents.md#permission-limits)); verify `rule:`/`loc:`/`evidence:` and severity, arbitrate `P0`–`P1` findings per [balancing](references/balancing.md) (plus quick `P2`/`DELETIONS` in one pass), cap at `2` rounds, and stop once active `P0`–`P1` blockers reach `PASS`.
1. **Ratchet recurring `P1`s**: when a reviewer flags the same `P1` defect pattern `>= 2` times across diffs/sessions, propose promoting it into a mechanical gate via [lesson-learned](../skillify/references/lesson-learned.md).

## Severity and Priority Balancing

`P0`–`P2` measures **lens-local defect severity** (`P0` severe/irreversible harm, `P1` material defect/contract break, `P2` non-blocking improvement; omit nits, no `P3`), while the coordinator arbitrates cross-lens `P1` collisions via optional project `Priorities` in `AGENTS.md` and logs overrides in a `Trade-Offs` table—see [balancing](references/balancing.md) for the canonical severity table, axis-to-lens map, and arbitration rules.

## Gotchas

- `agy` snapshots custom agents at startup—test edits in a fresh or headless session.
- In `fmind/dot`, global sources live in `dot_agents/supagents/`, follow the repo `AGENTS.md` supagents gate, keep discovery `< 2,000` tok, retire old roles in `.chezmoiremove`, and run `mise run apply`.

## Documentation

- [Authoring](references/authoring.md) · [Balancing](references/balancing.md) · [Calibration](references/calibration.md) · [Template](templates/reviewer.md) · [agent-supagents](https://github.com/fmind/agent-supagents) · Companions: [full-review](../full-review/SKILL.md), [humanize](../humanize/SKILL.md), [cross-harness-agents](../agent-harnesses/references/cross-harness-agents.md), [headless-review](../agent-harnesses/references/headless-review/GUIDE.md).
