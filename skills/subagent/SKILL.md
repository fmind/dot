---
name: subagent
description: "Design, research, compile, calibrate, and orchestrate read-only adversarial reviewer subagents via supagents or native host role files."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/subagent
  created: "2026-09-09"
  updated: "2026-11-17"
---

# Adversarial Reviewer Subagents

Keep content producers dynamic (built-in subagents + skills on demand). Encode quality gates as static, clean-context, read-only reviewer `supagents` outside the creation loop—never as same-session skills. Follow the 3-tier model: workstation `dot/` holds personal tools/preferences; global `fmind-review-*` holds stack-independent domain best practices; project `AGENTS.md`/`DESIGN.md`/`SECURITY.md` and `<org>-review-*` supagents override global defaults without weakening security or `Output Contract`.

## Global `fmind-review-*` Suite (33 Single-Discipline Roles)

Each role (`dot_agents/supagents/`, extending `_reviewer.md`) owns **one discipline** with self-contained operational checks, unrestricted file read + sanitized primary-source web lookup, zero step caps, and grounded `## Sources`:

- **Software, Quality & Languages (`8`)**: `completeness` (requirement traceability, zero stubs, state/doc sync, proof parity), `arch` (C4 bounds, `>= 2` options, rollback), `code` (logic, `< 500` LOC, YAGNI), `python` (typing, packaging, `asyncio` idioms), `shell` (POSIX/Bash/Fish quoting, traps, idempotency), `test` (behavior tests, mutation/edge strength), `cli` (streams, exit codes, TTY/flags), `api` (REST/gRPC/SDK schemas, RFC 9457, SemVer).
- **Infra, Platform, Security & FinOps (`8`)**: `terraform` (HCL modules, validation, state/`for_each`), `docker` (multi-stage, digests, non-root, `PID 1`), `k8s` (PSS `restricted`, probes, QoS/PDB, NetPol), `cicd` (Actions permissions, SHA pins, injection/OIDC), `sre` (N-1 rollouts, timeouts/jitter, drain, SLOs), `perf` (pools/semaphores, N+1, streaming, benchmarks), `security` (exploit paths, keyless IAM, trust, pins), `finops` (budgets, autoscale ceilings, scan/egress/LLM spend).
- **Data, SQL, ML & AI Agents (`7`)**: `sql` (grain/fan-out joins, `NULL` traps, pruning, exact decimals), `data` (contracts, UTC/units, idempotent `MERGE`/partitions, PII), `mlops` (baselines, split leakage, skew, drift), `agents` (min agency, MCP tool schemas, guardrails, trajectory evals), `rag` (contextual chunking, hybrid+rerank, chunk ACL pushdown, eval split), `skill` (`SKILL.md` routing, progressive disclosure, token budgets), `supagent` (single-lens scope, zero name-dropping, 5-block rubric, `Sources`).
- **Docs, Fact-Checking, Writing & Compliance (`5`)**: `readme` (10s pitch, 5-min quickstart, CLI parity), `docs` (doc-mode purity, navigation, recovery/lifecycle), `factcheck` (SAFE atomic claims, primary URLs, provenance, math), `human` (5s BLUF, anti-slop, link craft), `compliance` (SPDX/copyleft, ToS/tiers, GDPR/DPA, EU AI Act).
- **Visuals, Decks, UI/UX, Web & Pitch (`5`)**: `figures` (honest axes, Okabe-Ito CVD palettes, direct labels, source code), `deck` (assertion-evidence titles, ~30-word load, narrative spine), `design` (`DESIGN.md` tokens, usability, states, WCAG contrast), `web` (surface class, semantic HTML, CWV causes, SEO/`noindex`, CSP), `pitch` (15s BLUF, options/ROI deltas, proof, objections, single CTA).

## Author or Refresh Reviewers

Follow [authoring](references/authoring.md) end-to-end:

1. **Enforce 1 discipline = 1 supagent**: supagents have no progressive disclosure (`references/`); split multi-surface roles instead of stuffing two domains into one prompt.
1. **Research primary sources in parallel**: query official Google/Microsoft/AWS/Anthropic docs, IETF/W3C/OWASP/NIST/SLSA specs, and peer-reviewed papers; extract model-delta checks (`Invariant + Why + Defect Conditions + Evidence`) with zero `"Distills <Book>"` name-dropping and verify live `## Sources` URLs (`lychee`).
1. **Compile (`40`–`80` lines) & audit**: inherit `_reviewer` ([template](templates/reviewer.md) for standalone repos), run `supagents build --strict --project && supagents check --strict --project`, audit with `fmind-review-supagent`, and run [calibration](references/calibration.md).

## Coordinator-as-Critic Loop

1. **Deterministic gates first (`0` tokens)**: run linters, tests, scanners, `vale`, `lychee`, and PNG/PDF renders first.
1. **Prefer project overrides & fan out**: select repo `<org>-review-*` roles when present (else `fmind-review-*`), spawning `1`–`5` matching specialists in parallel—pairing `fmind-review-completeness` alongside domain roles on multi-part builds and external deliverables (e.g., `python` + `test` + `completeness`, or `deck` + `figures` + `factcheck` + `completeness`; pass `--settings '{"allowNonWorkspaceAccess":false}'` on untrusted checkouts).
1. **Audit findings**: verify every `rule:`, `loc:`, and `evidence:` against live files, apply verified `BLOCK`/`REVISE` fixes + `DELETIONS` (max `2` rounds), and stop on `PASS`.

## Gotchas

- **Session prompt caching**: active `agy`/`claude` sessions snapshot custom agents at startup; test edits in a fresh or headless session.
- **Chezmoi build**: in `fmind/dot`, run `mise run format:supagents && mise run check:supagents` (`supagents.yaml`), register retired roles in `.chezmoiremove`, and run `mise run apply`.

## Documentation

- [Authoring & Grounded Research](references/authoring.md) · [Calibration](references/calibration.md) · [Template](templates/reviewer.md) · [fmind/agent-supagents](https://github.com/fmind/agent-supagents) · Companions: [full-review](../full-review/SKILL.md), [humanize](../humanize/SKILL.md), [cross-harness-agents](../agent-project/references/cross-harness-agents.md), [headless-review](../agy/references/headless-review/GUIDE.md).
