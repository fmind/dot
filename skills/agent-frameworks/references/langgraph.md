---
name: langgraph
description: "LangGraph state, persistence, streaming, interrupts, and durable execution."
---

# LangGraph

Own the topology only when the workflow is more than "loop until done": classification before routing, parallel fan-out, or deterministic steps between model calls. [langchain](langchain.md)'s `create_agent` already returns a compiled graph that drops into a `StateGraph` as a node with its middleware intact; confirm it does not already cover the need before `uv add langgraph`.

## Workflow

1. **Choose persistence deliberately**: `InMemorySaver` is for tests only; `langgraph-checkpoint-sqlite`, `-postgres`, and `-mongodb` install separately. Postgres requires `.setup()` to create or migrate its schema (not a method on every checkpointer) and a `thread_id` under 255 characters; isolate threads per user and prove resume across a real process restart.
1. **Set durability per run, not at compile**: `durability="sync"` for high-value writes, `"async"` for the default trade-off, and `"exit"` only when losing intermediate state to a process crash is acceptable.
1. **Interrupt for review**: `interrupt()` and `Command(resume=...)` from `langgraph.types` on the same thread; resuming re-runs the node from its start, so make preceding writes idempotent.
1. **Configure failure behavior on `add_node`**: `retry_policy=RetryPolicy(...)`, `timeout=TimeoutPolicy(run_timeout=..., idle_timeout=...)`, and `error_handler=` instead of try/except in every node. Timeouts need async nodes (a sync node raises `ValueError`) and raise `NodeTimeoutError`, which the default retry policy retries; a handler receives the failure only through a parameter typed `NodeError` and returns a recovery `Command`.
1. **Drain workers on shutdown**: pass `control=RunControl()` (`langgraph.runtime`) and call `request_drain()` on SIGTERM; the run stops after the current superstep, raises `GraphDrained`, and resumes from its checkpoint with `invoke(None, config)`.
1. **Stream with `stream_mode`**: the typed `stream_events(..., version="v3")` API is experimental and emits `LangChainBetaWarning`; adopt it only with a test of its event shape against the locked release.

## Gotchas

- **Never wrap `interrupt()` in a broad `except`**: it pauses by raising, and a bare handler swallows the pause.
- **Interrupt matching is strictly index-based**: resume values match by position within the node, so a conditionally skipped or reordered `interrupt()` silently receives another call's answer; keep the calls unconditional and in a fixed order.
- **Checkpoints persist state and outlive deployments**: prompts, tool outputs, and any credential placed in state reach the store, so keep state minimal with access and retention controls; treat a state schema change as a migration rehearsed on a copy of real checkpoints.

## Official Skills

Upstream: [langchain-ai/langchain-skills](https://github.com/langchain-ai/langchain-skills) (`langgraph-fundamentals`, `langgraph-persistence`, `langgraph-human-in-the-loop`; `langgraph-cli` only for that deployment workflow). Apply the shared [vendor-skill policy](../../agent-project/references/vendor-skills.md) before a project-scoped installation.

## Documentation

- [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) · [Checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers) · [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) · [Fault tolerance](https://docs.langchain.com/oss/python/langgraph/fault-tolerance) · [Event streaming](https://docs.langchain.com/oss/python/langgraph/event-streaming)
- Releases: [changelog](https://docs.langchain.com/oss/python/releases/changelog) · [GitHub releases](https://github.com/langchain-ai/langgraph/releases)
- Live reference: the docs MCP endpoint `https://docs.langchain.com/mcp` answers for the current version.
- Companion skills: [python-async](../../python-stack/references/python-async/GUIDE.md) (cancellation and shutdown), [observability](../../python-stack/references/observability.md) (traces).
