---
name: subagent
description: "Design, compile, calibrate, and orchestrate read-only adversarial reviewer subagents per project (via supagents or native host role files)."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/subagent
  created: "2026-11-16"
  updated: "2026-11-16"
---

# Adversarial Reviewer Subagents

Encode taste, domain standards, and quality bars as clean-context, read-only reviewer subagents outside the creation loop—never as skills (which share polluted creator context and can be skipped). Aim for **one reviewer per relevant company specialist role as a target** (not a requirement), spawning only the `1`–`4` roles matching each change; use [skillify](../skillify/SKILL.md) for procedures and [task-prompts](../task-prompts/SKILL.md) for briefs.

## Global `fmind-review-*` Suite (13 Roles)

Workstation reviewers in `~/.agents/supagents/` (`dot_agents/supagents/`) check target-repo `AGENTS.md`, `DESIGN.md`, and `SECURITY.md` first (without weakening security or `Output Contract`) before applying distilled Google and industry standards:

- **Core Engineering**: `fmind-review-code` (Google CR standard, `< 500` LOC & anti-creep, test/mutation strength), `fmind-review-interface` (Google AIP + `clig.dev`, exception/exit/error contracts, typing, docs, versioning), `fmind-review-security` (SAIF/OWASP/SLSA threat paths, IAM, isolation, pins), `fmind-review-ops` (Google SRE rollouts, timeouts, maintainability, EOL/future-proofing), `fmind-review-perf` (`asyncio`/pools, N+1/memory bounds, measured baselines), `fmind-review-finops` (non-human cloud/storage/network/CI/SaaS/AI spend, budgets, alerts).
- **Data, ML & AI**: `fmind-review-data` (contracts, grain/joins, UTC, idempotency, PII), `fmind-review-mlops` (Google Rules of ML + ML Test Score: baselines, split leakage, train-serve skew, reproducibility, drift), `fmind-review-ai` (minimum agency, lean prompts/RAG/context, tool/MCP guardrails, multi-trial/judge evals).
- **Human, Visual, Web & Value**: `fmind-review-human` (length targets, medium-fitted beauty/colors/borders/typos/emphasis, zero AI slop/em-dashes/prose backticks), `fmind-review-design` (M3 calm hierarchy, `DESIGN.md` tokens, WCAG contrast), `fmind-review-web` (surface-adaptive HTML/a11y, CWV causes, SEO vs private `noindex`, agentic readiness), `fmind-review-pitch` (buyer hook, proof, objections, single CTA).

## Author Per-Project Reviewers

1. **Map company roles & isolate data**: inspect `AGENTS.md`, `DESIGN.md`, `SECURITY.md`, and active hosts. Prefix roles (`<org>-review-<role>` or `<org>-<stakeholder>`) without leaking customer names, URLs, or brand tokens across repos.
1. **Distill rulebooks inline (`<= 100` body lines; zero URL fetches)**: embed domain standards + `Do Not Flag` sibling-deferral rules directly (`~60`–`90` lines; zero main-session token cost) and read repo docs locally—read-only subagents block `WebFetch`/`search_web` against exfiltration and prompt injection.
1. **Compile or write native files**:
   - **Multi-harness via [`supagents`](https://github.com/fmind/agent-supagents) (recommended)**: start from [reviewer.md](templates/reviewer.md) in `.agents/supagents/<name>.md` (OpenCode V2 `permissions` denies `.env`/`.envrc` natively; `AGY`/`CLAUDE`/`COPILOT` enforce read-only tool allowlists and inherit path denies from host settings), then gate in `mise.toml`:
     ```bash
     supagents build --project --diff
     supagents build --project --strict
     supagents check --project --strict
     ```
   - **Native host files (single-harness or customer-constrained)**: write `.agents/agents/<role>.md`, `.claude/agents/<role>.md`, `.github/agents/<role>.agent.md`, or `.opencode/agents/<role>.md` per [cross-harness-agents](../agent-project/references/cross-harness-agents.md), copying the host's read-only frontmatter block from [reviewer.md](templates/reviewer.md) verbatim so tools never fail open.
1. **Enforce the Agent-to-Agent Output Contract**: require `VERDICT: PASS | REVISE | BLOCK` (`P0`/high-conf `P1` -> `BLOCK`, med-conf `P1`/`P2` -> `REVISE`, zero `P0`–`P2` -> `PASS`), redacted `evidence`, `DELETIONS`, and `UNVERIFIED` ([reviewer.md](templates/reviewer.md)), then run [seeded-defect calibration](references/calibration.md).

## Coordinator-as-Critic Loop

1. **Deterministic gates first (`0` tokens)**: pass formatters, `ruff`/`ty`/`pytest`, scanners, and `vale --config ~/.config/vale/.vale.ini --output=JSON <draft.md>` before delegating.
1. **Freeze, materialize diffs & fan out**: write git diffs to `/var/tmp/review-<id>.diff` (read-only subagents lack shell) and pass **explicit file paths** (never bare directories) + acceptance criteria in parallel.
1. **Audit the reviewers**: cross-check `loc` + `evidence` against live files—discard hallucinations, apply verified `BLOCK`/`REVISE` fixes + safe `DELETIONS` (escalating scope/spend/architecture calls to user `Decisions`; max `2` rounds), and stop on `PASS`.

## Gotchas

- **Session prompt caching**: active `agy`/`claude` sessions snapshot custom agents at startup—use a fresh session or headless CLI run after edits.
- **Markers & chezmoi**: migrate handwritten files before building, exclude generated dirs from `dprint`/`.ignore`, and in `fmind/dot` use `--project --source-dir dot_agents/supagents --config supagents.yaml` + `mise run apply` (never `--global`).

## Documentation

- [Calibration](references/calibration.md) · [Template](templates/reviewer.md) · [fmind/agent-supagents](https://github.com/fmind/agent-supagents) · Companions: [full-review](../full-review/SKILL.md), [humanize](../humanize/SKILL.md), [cross-harness-agents](../agent-project/references/cross-harness-agents.md), [headless-review](../agy/references/headless-review/GUIDE.md).
