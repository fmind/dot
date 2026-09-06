---
name: loop-engineering
description: Design or simplify sustained agent work as inner, middle, and outer loops, with judgment in skills and deterministic helpers in a Python CLI. Use when engineering an agent loop.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/loop-engineering
  created: "2026-09-06"
  updated: "2026-09-06"
---

# Loop Engineering

Design the smallest durable system that can learn, resume, stop, and prove what happened. This skill owns loop architecture; [product-loop](../product-loop/SKILL.md) owns product discovery and launch decisions.

## Workflow

1. **Define the decisions**: State the objective, evidence that can change direction, authority, budget or horizon, external side effects, and hard stop conditions. Separate scientific or task success from operational completion.
1. **Challenge the topology**: Keep a layer only when it closes a distinct feedback horizon. Merge any layer that merely renames another role.

   | Loop   | Decision horizon                 | Owns                                                                                   | Exit contract                                      |
   | ------ | -------------------------------- | -------------------------------------------------------------------------------------- | -------------------------------------------------- |
   | Inner  | One hypothesis or work item      | Controls, one bounded action, observation, verdict, and item checkpoint                | Return after one evidence-producing action         |
   | Middle | One campaign or portfolio window | Prioritization, resource allocation, live reconciliation, reports, blockers, and waits | Stop at the horizon or return the exact checkpoint |
   | Outer  | Several completed loop outcomes  | Constraint analysis and reversible improvements to skills or helpers                   | Validate and finish one owner-invoked review       |

1. **Choose minimal durable state**: Prefer a human-readable portfolio checkpoint, one checkpoint per work item, an append-only event log, concise sourced lessons, and derived reports. Give every fact one owner; do not create a second task database.
1. **Write the agent skills**: Create one narrowly routed skill per retained loop using [the loop skill contracts](references/skill-contracts.md). Put research, critique, implementation, and reflection inside the loop step that needs them instead of scheduling role-shaped loops.
1. **Build only deterministic helpers**: Use [cli-contracts](../cli-contracts/SKILL.md) and [python-stack](../python-stack/SKILL.md) for a small typed CLI run through `uv`. Useful commands validate scope and records, enforce transitions, append atomically, deduplicate launches, reconcile uncertain external operations, verify source or artifact identity, expose status, and render report context.
1. **Keep the CLI one-shot**: Each command performs one explicit operation and exits. It must not select hypotheses, allocate the portfolio, launch agent harnesses, schedule itself, interpret unchanged blockers as progress, or decide whether evidence merits promotion.
1. **Engineer recovery before continuity**: Check current local and live state before action. Reconcile an interrupted or timed-out external mutation before retrying it, record unknown outcomes explicitly, and use only the active harness's native continuation or bounded wait when continuity is authorized.
1. **Test the failure boundaries**: Unit-test parsing, transitions, locking, idempotency, exact identity checks, and malformed evidence. Replay success, negative evidence, interruption, ambiguous timeout, exhausted capacity, stale wake-up, and explicit stop with offline fakes; keep live proof separate.
1. **Review for deletion**: Start with skills and plain files. Add a CLI helper only after a recurring mechanical operation is demonstrated; remove supervisors, duplicate roles, receipt layers, and workflow state machines that do not protect a concrete invariant.

## Gotchas

- **Authority does not compose**: Invoking a loop skill does not authorize spending, submissions, publication, deployment, commits, or other external effects absent from the current request.
- **Stop is a state transition**: Cancel waits, retries, successors, and new work promptly; checkpoint in-flight facts. A stale continuation must read the stopped state and perform no work.
- **Receipts are not outcomes**: A process, local ledger row, queued job, or successful request proves only that stage. Refresh the authoritative system before claiming completion or retrying.
- **Outer means intentional**: The outer loop is owner-invoked by default. Do not hide it in a timer or let it weaken domain rules, evidence thresholds, or authority boundaries.
- **Private provenance stays private**: When generalizing a private workflow, retain only reusable invariants; remove names, targets, providers, paths, measurements, budgets, credentials, and copied logs.

## Documentation

- Companion skills: [skillify](../skillify/SKILL.md) (package authoring), [prompt-design](../prompt-design/SKILL.md) (instruction and tool boundaries), [quality-assurance](../quality-assurance/SKILL.md) (risk-based scenario validation).
