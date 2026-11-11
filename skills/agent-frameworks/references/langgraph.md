---
name: langgraph
description: "LangGraph state, persistence, streaming, interrupts, and durable execution."
---

# LangGraph

Hand-write `StateGraph` topology only beyond a tool loop (pre-routing classification, parallel fan-out, deterministic steps between LLM calls); [langchain](langchain.md)'s `create_agent` already compiles a graph usable as a `StateGraph` node with middleware intact.

## Workflow

1. **Choose persistence**: keep `InMemorySaver` to tests; install `langgraph-checkpoint-sqlite`, `-postgres` (call `.setup()` for schema migrations; keep `thread_id` <255 chars), or `-mongodb`. Isolate threads per user and test resume across a process restart.
1. **Set durability per run**: `durability="sync"` for critical writes, `"async"` by default, `"exit"` only when crash loss of intermediate steps is acceptable.
1. **Interrupt safely**: pair `interrupt()` with `Command(resume=...)` (`langgraph.types`) on the same thread; resuming replays the node from start, so keep prior side effects idempotent.
1. **Declare node policies on `add_node`**: use `retry_policy=RetryPolicy(...)`, `timeout=TimeoutPolicy(run_timeout=..., idle_timeout=...)` (async nodes only—sync raises `ValueError`; raises retriable `NodeTimeoutError`), and `error_handler=` (parameter typed `NodeError` returning a `Command`) instead of per-node `try/except`.
1. **Drain on shutdown**: pass `control=RunControl()` (`langgraph.runtime`), call `request_drain()` on SIGTERM (stops after the superstep with `GraphDrained`), and resume via `invoke(None, config)`.
1. **Stream with `stream_mode`**: `stream_events(..., version="v3")` emits `LangChainBetaWarning`; pin and test event shapes before adopting.

## Gotchas

- **Never catch `interrupt()` broadly**: bare `except` blocks swallow the pause exception.
- **Keep `interrupt()` order fixed**: resume answers match by call index inside a node, so conditional or reordered `interrupt()` calls misroute values.
- **Treat checkpoints as durable data**: prompts, outputs, and anything in state persist across deploys—keep secrets out of state, enforce access/retention, and rehearse state-schema migrations on copied checkpoints.

## Official Skills

Upstream: [langchain-ai/langchain-skills](https://github.com/langchain-ai/langchain-skills) (`langgraph-fundamentals`, `langgraph-persistence`, `langgraph-human-in-the-loop`, plus `langgraph-cli` when needed); vet per [vendor-skill policy](../../agent-project/references/vendor-skills.md).

## Documentation

- [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) · [Checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers) · [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) · [Fault tolerance](https://docs.langchain.com/oss/python/langgraph/fault-tolerance) · [Event streaming](https://docs.langchain.com/oss/python/langgraph/event-streaming)
- Releases: [changelog](https://docs.langchain.com/oss/python/releases/changelog) · [GitHub releases](https://github.com/langchain-ai/langgraph/releases)
- Live docs MCP: `https://docs.langchain.com/mcp`.
- Companion skills: [python-async](../../python-stack/references/python-async/GUIDE.md), [observability](../../python-stack/references/observability.md).
