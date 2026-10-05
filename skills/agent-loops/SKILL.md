---
name: agent-loops
description: "Design agent goals, loops, checkpoints, recovery, and stop conditions."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-loops
  created: "2026-09-06"
  updated: "2026-10-05"
---

# Agent Loops

Design the smallest durable system that can learn, resume, stop, and prove what happened. This skill owns loop architecture; [product-loop](../product-loop/SKILL.md) owns product discovery and launch decisions.

## Workflow

1. **Define the decisions**: State the objective, evidence that can change direction, authority, budget or horizon, external side effects, and hard stop conditions. Separate scientific or task success from operational completion.
1. **Make the goal the driver**: Use the active harness's native `/goal` when the user requests a sustained goal. Define whether completion means an evidenced objective, a finished time window, or an objective bounded by a deadline. Follow [goals, prompts and continuation](references/goals-and-prompts.md); verify actual host capabilities instead of implementing another goal engine.
1. **Challenge the topology**: Keep a layer only when it closes a distinct feedback horizon. Merge any layer that merely renames another role. Read [loop topology](references/topology.md) when several decision horizons are needed.
1. **Choose minimal durable state**: Prefer a human-readable portfolio checkpoint, one checkpoint per work item, an append-only event log, concise sourced lessons, and derived reports. Give every fact one owner; do not create a second task database. For explicitly assigned concurrent sessions, record disjoint work scope, session identity, shared writer and account-wide resource allocation before writes.
1. **Write the agent skills**: Create one narrowly routed skill per retained loop using [the loop skill contracts](references/skill-contracts.md). Put research, critique, implementation, and reflection inside the loop step that needs them instead of scheduling role-shaped loops.
1. **Keep entry prompts thin**: Project `prompts/run.md` and `prompts/improve.md` read `AGENTS.md`, load the owning skill and pass the goal scope, per [thin project prompts](references/goals-and-prompts.md#thin-project-prompts); skills own procedure and stop rules. Add a named start prompt only for a real session assignment or distinct scenario.
1. **Add helpers only for demonstrated mechanics**: After a recurring mechanical operation is demonstrated, build a one-shot typed CLI per [deterministic helpers](references/skill-contracts.md#deterministic-helpers); it never makes the loop's judgment calls.
1. **Engineer recovery before continuity**: A process, local ledger row, queued job, or successful request proves only that stage. Refresh the authoritative local and live state before acting, claiming completion, or retrying; reconcile an interrupted or timed-out external mutation before retrying it, record unknown outcomes explicitly, and use only the active harness's native continuation or bounded wait when continuity is authorized.
1. **Test the failure boundaries**: Unit-test parsing, transitions, locking, idempotency, exact identity checks, and malformed evidence. Replay success, negative evidence, interruption, ambiguous timeout, exhausted capacity, stale wake-up, and explicit stop with offline fakes; keep live proof separate.
1. **Review for deletion**: Start with skills and plain files; remove supervisors, duplicate roles, receipt layers, and workflow state machines that do not protect a concrete invariant.

## Gotchas

- **Authority does not compose**: Invoking a loop skill does not authorize spending, submissions, publication, deployment, commits, or other external effects absent from the current request.
- **Stop is a state transition**: Cancel waits, retries, successors, and new work promptly; checkpoint in-flight facts. A stale continuation must read the stopped state and perform no work.
- **Time is not success**: A deadline proves a window ended, not continuous execution or domain success. A result, report, compaction or empty queue is not the end of a still-active campaign; continue useful work or an actual bounded wait.
- **Budgets are ceilings**: Available tokens, compute or time do not justify unchanged queries, unsupported experiments or lower admission gates. Stable blockers need a reopening signal and evidence-review cadence.
- **Outer means intentional**: The outer loop is owner-invoked by default. Do not hide it in a timer or let it weaken domain rules, evidence thresholds, or authority boundaries.
- **Private provenance stays private**: When generalizing a private workflow, retain only reusable invariants; remove names, targets, providers, paths, measurements, budgets, credentials, and copied logs.

## Documentation

- Companion skills: [skillify](../skillify/SKILL.md) (package authoring), [prompt-design](../prompt-design/SKILL.md) (instruction and tool boundaries), [quality-assurance](../quality-assurance/SKILL.md) (risk-based scenario validation).
