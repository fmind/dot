---
name: langgraph
description: Build stateful Python workflows with LangGraph. Use for StateGraph, reducers, checkpoints, streaming, interrupts, and durable resume.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/langgraph
  created: "2026-09-10"
  updated: "2026-09-12"
---

# LangGraph

Own the topology when the workflow is more than "loop until done": classification before routing, parallel fan-out, or deterministic steps between model calls. [langchain](../langchain/SKILL.md)'s `create_agent` already returns a compiled graph that drops into a `StateGraph` as a node with its middleware intact, so reach here for the surrounding structure, the persistence contract, and resumable execution.

## Workflow

1. **Scope the graph first**: confirm `create_agent` plus middleware does not already cover it, then write down state fields, node inputs and outputs, stop conditions, and every side effect before `uv add langgraph`.
1. **Build explicitly**: a `StateGraph` with typed state, small nodes, and edges from `START` to `END`. Define reducers only for fields that combine concurrent updates; unreduced concurrent writes raise `INVALID_CONCURRENT_GRAPH_UPDATE`.
1. **Run it deterministically**: compile and execute with no provider, asserting final state, routing, and error paths. Bound the run with `graph.invoke({...}, {"recursion_limit": N})` before adding model nodes.
1. **Choose persistence deliberately**: `InMemorySaver` (`langgraph.checkpoint.memory`) is for tests only; `langgraph-checkpoint-sqlite`, `-postgres`, and `-mongodb` install separately (`uv add langgraph-checkpoint-postgres`). Call `.setup()` once per store, keep `thread_id` stable and under 255 characters, isolate threads per user, and prove resume across a real process restart.
1. **Set durability per run, not at compile**: pass `durability="sync"` for high-value writes, `"async"` for the default trade-off, and `"exit"` only when losing a mid-run crash is acceptable — `"exit"` persists nothing until execution ends.
1. **Interrupt for review**: `from langgraph.types import interrupt, Command`, resume with `Command(resume=...)` on the same thread, and rehearse approve, reject, timeout, and repeated resume. Resuming re-runs the node from its start, so make preceding writes idempotent.
1. **Configure failure behavior**: set `RetryPolicy`, run and idle timeouts, and graph-level defaults rather than wrapping every node in try/except; handle `NodeTimeoutError`, route recoverable failures with `Command`, and add the SIGTERM drain pattern before deploying a worker.
1. **Stream through the typed API**: prefer `stream_events(..., version="v3")` for new applications and reserve `stream_mode` values (`updates`, `values`, `messages`, `custom`, `checkpoints`, `tasks`, `debug`) for existing consumers; emit progress from inside nodes with `get_stream_writer()`.
1. **Version the state**: checkpoints outlive a deployment, so treat a state or channel schema change as a migration and rehearse recovery with [data-migration](../data-migration/SKILL.md).

## Gotchas

- **Never wrap `interrupt()` in a broad `except`**: it pauses by raising, and a bare handler swallows the pause. Keep error-prone work in a separate node.
- **Interrupt matching is strictly index-based**: resume values are matched by position within the node, so a conditionally skipped or reordered `interrupt()` silently receives another call's answer. Keep the calls unconditional and in a fixed order, and return simple values from them.
- **Checkpoints retain what you put in state**: prompts, tool outputs, and any credential accidentally placed in a field persist to the store; keep state minimal and apply access and retention controls.
- **Persistence is not a scheduler**: a durable checkpoint does not prove a stopped worker will ever wake up to resume it. See [scheduled-jobs](../scheduled-jobs/SKILL.md).

## Official Skills

Upstream: [langchain-ai/langchain-skills](https://github.com/langchain-ai/langchain-skills). Use `ecosystem-primer` for the package boundaries, then `langgraph-fundamentals`, `langgraph-persistence`, and `langgraph-human-in-the-loop`; take `langgraph-cli` only for that deployment workflow. The bundle ships as an npm package with `install.sh` and `.claude-plugin`, keeps its skills under `config/skills/`, and carries no license file, so confirm the discovery path and apply the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) before installing a project-scoped selection.

## Documentation

- [Overview](https://docs.langchain.com/oss/python/langgraph/overview) · [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) · [Checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers) · [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) · [Fault tolerance](https://docs.langchain.com/oss/python/langgraph/fault-tolerance) · [Event streaming](https://docs.langchain.com/oss/python/langgraph/event-streaming)
- Releases: [changelog](https://docs.langchain.com/oss/python/langgraph/changelog-py) · [GitHub releases](https://github.com/langchain-ai/langgraph/releases) · [v1 release notes](https://docs.langchain.com/oss/python/releases/langgraph-v1)
- Live reference: the docs expose an MCP endpoint at `https://docs.langchain.com/mcp` for version-current answers.
- Companion skills: [langchain](../langchain/SKILL.md) (agent loop and models), [python-async](../python-async/SKILL.md) (cancellation and shutdown), [observability](../observability/SKILL.md) (traces), [agent-evaluation](../agent-evaluation/SKILL.md) (quality comparisons).
