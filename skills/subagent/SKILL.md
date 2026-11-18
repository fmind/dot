---
name: subagent
description: "Design, research, compile, calibrate, and orchestrate read-only adversarial reviewer subagents via supagents or native host role files."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/subagent
  created: "2026-09-09"
  updated: "2026-11-18"
---

# Adversarial Reviewer Subagents

Keep content producers dynamic (built-in subagents + skills on demand). Encode quality gates as static, clean-context, read-only reviewer `supagents` outside the creation loop—never as same-session skills. Follow the 3-tier model: workstation `dot/` holds personal tools/preferences; global `fmind-review-*` holds stack-independent domain best practices; project `AGENTS.md`/`DESIGN.md`/`SECURITY.md` and `<org>-review-*` supagents override global defaults without weakening security or `Output Contract`.

## Global `fmind-review-*` Suite (34 Single-Discipline Roles)

Each role (`dot_agents/supagents/`, extending `_reviewer.md`) owns **one discipline** with self-contained operational checks, full file read + non-mutating diagnostic shell/Chrome/Playwright + sanitized primary-source web lookup, zero file-edit/delegation tools, zero step caps, and grounded `## Sources`:

- **Software & Languages (`8`)**: `completeness` (requirement traceability, zero stubs, state/doc/proof parity), `architecture` (C4 bounds, options, rollback), `code` (logic, `< 500` LOC, YAGNI), `python`, `shell`, `test` (behavior, mutation/edge strength), `cli` (streams, exits, TTY/flags), `api` (REST/gRPC/SDK, RFC 9457, SemVer).
- **Infra, Reliability, Security & FinOps (`8`)**: `terraform`, `docker`, `k8s`, `cicd`, `sre` (rollouts, timeouts/jitter, drain, SLOs), `perf` (pools, N+1, streaming, benchmarks), `security` (exploit paths, keyless IAM, trust, pins), `finops` (budgets, autoscale ceilings, unit spend).
- **Data, SQL, ML & AI (`7`)**: `sql`, `data`, `mlops`, `agents` (min agency, tool schemas, guardrails, trajectory evals), `rag` (chunking, hybrid+rerank, ACL pushdown, eval split), `skill` (`SKILL.md` routing, progressive disclosure, budgets), `supagent` (single-lens scope, 5-block rubric, `Sources`).
- **Docs, Fact-Checking, Writing & Legal (`5`)**: `readme`, `docs`, `factcheck` (atomic claims, primary URLs, math), `human` (BLUF, anti-slop, link craft), `compliance` (SPDX/copyleft, ToS, GDPR/DPA, EU AI Act).
- **Visuals, Decks, UI/UX, Web, Pitch & Estimation (`6`)**: `figures`, `deck`, `design` (`DESIGN.md` tokens, states, WCAG contrast), `web` (HTML/ARIA, CWV, SEO/`noindex`, CSP), `pitch` (BLUF, options/ROI, proof, single CTA), `estimate` (WBS, `P10`/`P50`/`P90` ranges, multipliers, critical path, scope/rate math).

## Author or Refresh Reviewers

Follow [authoring](references/authoring.md) end-to-end:

1. **Enforce 1 discipline = 1 supagent**: supagents have no progressive disclosure (`references/`); split multi-surface roles instead of stuffing two domains into one prompt.
1. **Research primary sources in parallel**: query official vendor docs, IETF/W3C/OWASP/NIST/SLSA specs, and peer-reviewed papers; extract model-delta checks (`Invariant + Why + Defect Conditions + Evidence`) with zero `"Distills <Book>"` name-dropping and verify live `## Sources` URLs (`lychee`).
1. **Compile (`40`–`80` lines) & audit**: inherit `_reviewer` ([template](templates/reviewer.md) for standalone repos), run `supagents build --strict --project && supagents check --strict --project`, audit with `fmind-review-supagent`, and run [calibration](references/calibration.md).

## Coordinator-as-Critic Loop

1. **Deterministic gates first (`0` tokens)**: run linters, tests, scanners, `vale`, `lychee`, and PNG/PDF renders first.
1. **Prefer project overrides & fan out**: select repo `<org>-review-*` roles when present (else `fmind-review-*`), spawning `1`–`5` specialists in parallel—pairing `fmind-review-completeness` alongside domain roles on multi-part builds and external deliverables (pass target paths, live dev URLs, or rendered PNGs in the brief, and add `--sandbox --settings '{"allowNonWorkspaceAccess":false}'` on untrusted checkouts).
1. **Audit findings**: verify every `rule:`, `loc:`, and `evidence:` against live files, apply verified `BLOCK`/`REVISE` fixes + `DELETIONS` (max `2` rounds), and stop on `PASS`.

## Gotchas

- **Session prompt caching**: active `agy`/`claude` sessions snapshot custom agents at startup; test edits in a fresh or headless session.
- **Chezmoi build & discovery budget**: in `fmind/dot`, run `mise run format:supagents && mise run check:supagents && uv run --frozen --project dot pytest -c dot/pyproject.toml -q tests/test_reviewer_subagents.py` (`supagents.yaml`), keep subagent discovery below `2,000` estimated tokens per scope (`dot context --source . --project .`), register retired roles in `.chezmoiremove`, and run `mise run apply`.

## Documentation

- [Authoring & Grounded Research](references/authoring.md) · [Calibration](references/calibration.md) · [Template](templates/reviewer.md) · [fmind/agent-supagents](https://github.com/fmind/agent-supagents) · [releases](https://github.com/fmind/agent-supagents/releases) · Companions: [full-review](../full-review/SKILL.md), [humanize](../humanize/SKILL.md), [cross-harness-agents](../agent-project/references/cross-harness-agents.md), [headless-review](../agy/references/headless-review/GUIDE.md).
