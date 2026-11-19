---
name: subagent
description: "Design, research, compile, calibrate, and orchestrate read-only adversarial reviewer subagents via supagents or native host role files."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/subagent
  created: "2026-09-09"
  updated: "2026-11-19"
---

# Adversarial Reviewer Subagents

Keep producers dynamic (built-in subagents + skills). Encode quality gates as static, clean-context, read-only reviewer `supagents` outside the creation loop—never same-session skills. Follow 3-tier scope: `dot/` owns personal tools; global `fmind-review-*` owns stack-independent best practices; project `AGENTS.md`/`DESIGN.md`/`SECURITY.md` and `<org>-review-*` override defaults without weakening security or `Output Contract`.

## Global `fmind-review-*` Suite (34 Single-Discipline Roles)

Each role (`dot_agents/supagents/`) owns **one discipline** with 2-tier least privilege (`_reviewer.md` air-gapped read-only for 33 roles including `design`/`web`, `_reviewer_web.md` sanitized public lookup for `factcheck`), zero shell/MCP/edit/delegation tools, host-native secret-path denies (Claude/AGY host settings + OpenCode `action: read` with `grep` omitted on `_reviewer_web`; Copilot lacks path denies), zero step caps, and grounded `## Sources`:

- **Software & Languages (`8`)**: `completeness` (requirement traceability, zero stubs, state/doc/proof parity), `architecture` (C4 bounds, options, rollback), `code` (logic, `< 500` LOC, YAGNI), `python`, `shell`, `test` (behavior, mutation/edge strength), `cli` (streams, exits, TTY/flags), `api` (REST/gRPC/SDK, RFC 9457, SemVer).
- **Infra, Reliability, Security & FinOps (`8`)**: `terraform`, `docker`, `k8s`, `cicd`, `sre` (rollouts, timeouts/jitter, drain, SLOs), `perf` (pools, N+1, streaming, benchmarks), `security` (exploit paths, keyless IAM, trust, pins), `finops` (budgets, autoscale ceilings, unit spend).
- **Data, SQL, ML & AI (`7`)**: `sql`, `data`, `mlops`, `agents` (min agency, tool schemas, guardrails, trajectory evals), `rag` (chunking, hybrid+rerank, ACL pushdown, eval split), `skill` (`SKILL.md` routing, progressive disclosure, budgets), `supagent` (single-lens scope, 5-block rubric, `Sources`).
- **Docs, Fact-Checking, Writing & Legal (`5`)**: `readme`, `docs`, `factcheck` (atomic claims, primary URLs, math), `human` (BLUF, anti-slop, link craft), `compliance` (SPDX/copyleft, ToS, GDPR/DPA, EU AI Act).
- **Visuals, Decks, UI/UX, Web, Pitch & Estimation (`6`)**: `figures`, `deck`, `design` (`DESIGN.md` tokens, states, WCAG contrast), `web` (HTML/ARIA, CWV, SEO/`noindex`, CSP), `pitch` (BLUF, options/ROI, proof, single CTA), `estimate` (WBS, `P10`/`P50`/`P90` ranges, multipliers, critical path, scope/rate math).

## Author or Refresh Reviewers

Follow [authoring](references/authoring.md) end-to-end:

1. **Enforce 1 discipline = 1 supagent**: no progressive disclosure (`references/`); split multi-surface roles.
1. **Research primary sources**: query official docs, IETF/W3C/OWASP/NIST/SLSA specs, and papers; write model-delta rules (`Invariant + Why + Defects + Evidence`) with zero `"Distills <Book>"` shorthand and live `## Sources` (`lychee`).
1. **Compile (`40`–`80` lines) & audit**: inherit `_reviewer` (or `_reviewer_web` for live public fact-checking; [template](templates/reviewer.md) for standalone repos), run `supagents build --strict --project && supagents clean --project && supagents check --strict --project`, audit with `fmind-review-supagent`, and run [calibration](references/calibration.md).

## Coordinator-as-Critic Loop

1. **Deterministic gates & renders first (`0` tokens)**: run linters, tests, scanners, `vale`, `lychee`, and Chrome/Playwright PNG/DOM/a11y/CSP/CWV/header captures first so reviewers inspect outputs with zero shell or browser-MCP access.
1. **Prefer project overrides & fan out**: spawn `1`–`5` `<org>-review-*` (or `fmind-review-*`) roles in parallel, pairing `fmind-review-completeness` on multi-part work. Supply explicit file lists, frozen diffs, symbol searches, logs, and `/tmp` PNGs/DOM dumps (`agy` 1.5.x CLI binds `read_file`/`finish`, plus `search_web` on `_reviewer_web`, dropping IDE-only search/fetch tools). Add `--sandbox --settings '{"allowNonWorkspaceAccess":false}'` on untrusted checkouts, and run `fmind-review-factcheck` from an isolated `/var/tmp/<sandbox>` holding sanitized extracts on secret-bearing repos (AGY/Copilot frontmatter lack per-agent secret denies).
1. **Audit findings**: verify every `rule:`, `loc:`, and `evidence:` against live files, apply verified `BLOCK`/`REVISE` fixes + `DELETIONS` (max `2` rounds), and stop on `PASS`.

## Gotchas

- **Session prompt caching**: active `agy`/`claude` sessions snapshot custom agents at startup; test edits in a fresh or headless session.
- **Chezmoi build & discovery budget**: in `fmind/dot`, run `mise run format:supagents && mise run check:supagents && uv run --frozen --project dot pytest -c dot/pyproject.toml -q tests/test_reviewer_subagents.py` (`supagents.yaml`), keep subagent discovery below `2,000` estimated tokens per scope (`dot context --source . --project .`), register retired roles in `.chezmoiremove`, and run `mise run apply`.

## Documentation

- [Authoring & Grounded Research](references/authoring.md) · [Calibration](references/calibration.md) · [Template](templates/reviewer.md) · [fmind/agent-supagents](https://github.com/fmind/agent-supagents) · [releases](https://github.com/fmind/agent-supagents/releases) · Companions: [full-review](../full-review/SKILL.md), [humanize](../humanize/SKILL.md), [cross-harness-agents](../agent-project/references/cross-harness-agents.md), [headless-review](../agy/references/headless-review/GUIDE.md).
