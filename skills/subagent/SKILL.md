---
name: subagent
description: "Design, compile, calibrate, and orchestrate read-only adversarial reviewer subagents per project (via supagents or native host role files)."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/subagent
  created: "2026-09-09"
  updated: "2026-11-16"
---

# Adversarial Reviewer Subagents

Keep content producer agents dynamic (built-in subagents paired with skills on the fly for maximum implementation flexibility). Encode taste and domain standards solely as static, clean-context, read-only reviewer `supagents` outside the creation loop—never as skills (which share polluted creator context). Spawn `1`–`4` matching specialists per change; use [skillify](../skillify/SKILL.md) for procedures and [task-prompts](../task-prompts/SKILL.md) for briefs.

## Global `fmind-review-*` Suite (17 Roles)

Workstation reviewers (`dot_agents/supagents/`, inheriting `_reviewer.md`) check `AGENTS.md` (plus `DESIGN.md`/`SECURITY.md` when relevant) before applying Google and industry standards ([standards manifest](references/standards.md)):

| Role                      | Focus                                                           |
| ------------------------- | --------------------------------------------------------------- |
| `fmind-review-arch`       | C4 bounds, `>= 2` options, boring tech, lock-in, rollback       |
| `fmind-review-code`       | Google CR, `< 500` LOC, YAGNI, behavior tests, concurrency      |
| `fmind-review-interface`  | Google AIP + `clig.dev`, exit/error codes, typing, SemVer       |
| `fmind-review-security`   | SAIF/OWASP/SLSA exploit paths, keyless IAM, trust, pins         |
| `fmind-review-ops`        | SRE expand-contract rollouts, timeouts, lifecycle, SLOs         |
| `fmind-review-perf`       | `asyncio`/pools, N+1/`O(n^2)`, memory, cold start, baselines    |
| `fmind-review-finops`     | Non-human cloud/CI/AI spend levers, billing alerts, quotas      |
| `fmind-review-data`       | Contracts, grain/joins, UTC/units, idempotent merges, PII       |
| `fmind-review-mlops`      | Rules of ML + ML Test Score: baselines, leakage, skew, drift    |
| `fmind-review-ai`         | Min agency, lean prompts/RAG splits, MCP guardrails, evals      |
| `fmind-review-compliance` | SPDX OSS/model/data/font licenses, ToS/DPA, GDPR, AI Act        |
| `fmind-review-docs`       | Diataxis modes, 5-min quickstarts, code sync, `< 1,500`t skills |
| `fmind-review-factcheck`  | SAFE atomic claims, `https://` public lookup, `Sources`, math   |
| `fmind-review-human`      | 5-sec BLUF, medium-proportional craft, links, zero AI slop      |
| `fmind-review-design`     | Active `DESIGN.md`, M3 hierarchy, Nielsen, WCAG, PNG/PDFs       |
| `fmind-review-web`        | Surface type, WCAG 2.2 AA, CWV causes, SEO/noindex, HTTP        |
| `fmind-review-pitch`      | Minto BLUF exec memos, Dunford/PR-FAQ, options, single CTA      |

## Author Per-Project Reviewers

1. **Map roles & isolate data**: inspect `AGENTS.md`, `DESIGN.md`, and `SECURITY.md`. Prefix roles (`<org>-review-<role>`) without leaking customer names, URLs, or brand tokens across repos.
1. **Inline model-delta (`<= 80` compiled body lines)**: follow the 3-tier model-delta strategy ([standards](references/standards.md)); embed concise checks + `Do Not Flag` without copying guidebooks or fetching rules at runtime.
1. **Compile via [`supagents`](https://github.com/fmind/agent-supagents) (`>= 1.6.0`) or native files**: keep shared host permissions, `{{BODY}}`, and `Output Contract` once in `.agents/supagents/_reviewer.md`, extending via `extends: _reviewer` ([reviewer.md](templates/reviewer.md) holds standalone blocks):
   ```bash
   supagents build --project --diff && supagents build --strict --project && supagents check --strict --project
   ```
1. **Enforce Output Contract & calibrate**: require `VERDICT: PASS | REVISE | BLOCK`, redacted `evidence`, `DELETIONS`, and `UNVERIFIED`, then run [calibration](references/calibration.md).

## Coordinator-as-Critic Loop

1. **Deterministic gates first (`0` tokens)**: run linters, tests, scanners, `vale --output=JSON`, `lychee`, and Playwright/Typst PNG renders before delegating so reviewers inspect concrete outputs with zero shell access.
1. **Freeze, isolate & fan out**: write repo diffs to an untracked workspace scratch file when confining reads (`--settings '{"allowNonWorkspaceAccess":false}'` on headless `agy`); when running `fmind-review-factcheck` inside secret-bearing customer workspaces, launch it from an isolated `/var/tmp/<sandbox>` directory holding only sanitized claim extracts or public deliverables; fan out `1`–`4` specialists in parallel.
1. **Audit findings**: verify every `loc` + `evidence` against live files, apply verified fixes + `DELETIONS` (max `2` rounds), and stop on `PASS`.

## Gotchas

- **Session prompt caching**: active `agy`/`claude` sessions snapshot custom agents at startup; use a fresh session or headless run after edits.
- **Markers & chezmoi**: migrate handwritten files first, exclude generated dirs from `dprint`/`.ignore`, and in `fmind/dot` pass `--project --source-dir dot_agents/supagents --config supagents.yaml` + `mise run apply`.

## Documentation

- [Standards](references/standards.md) · [Calibration](references/calibration.md) · [Template](templates/reviewer.md) · [fmind/agent-supagents](https://github.com/fmind/agent-supagents) · Companions: [full-review](../full-review/SKILL.md), [humanize](../humanize/SKILL.md), [cross-harness-agents](../agent-project/references/cross-harness-agents.md), [headless-review](../agy/references/headless-review/GUIDE.md).
