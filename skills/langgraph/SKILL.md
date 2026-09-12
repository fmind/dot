---
name: langgraph
description: Build stateful Python workflows with LangGraph. Use for StateGraph, reducers, checkpoints, streaming, interrupts, and durable resume.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/langgraph
  created: "2026-09-10"
  updated: "2026-09-11"
---

# LangGraph

Use LangGraph when the application needs explicit execution state; [langchain](../langchain/SKILL.md) owns model integrations and ordinary tool-calling agents.

## Workflow

1. Inspect the locked graph and checkpoint packages; use `uv add langgraph` when missing. Write down state fields, node inputs/outputs, stop conditions, and side effects.
1. Build a `StateGraph` with typed state, small nodes, and explicit edges from `START` to `END`. Define reducers only for fields that combine concurrent updates.
1. Compile and run a deterministic graph without a provider. Assert final state, routing, error paths, and a bounded recursion limit before adding model nodes.
1. When resume is required, select a checkpointer and stable `thread_id`; use an in-memory saver only for local tests. Isolate users' threads and test the production store across process restart.
1. Use `interrupt()` for review and `Command(resume=...)` on the same thread. Rehearse approve, reject, timeout, and repeated resume; make writes idempotent because resumed nodes can execute again.
1. Test streaming event handling, cancellation, concurrent state updates, and checkpoint schema changes before deployment.

## Gotchas

- Do not wrap interrupts in broad exception handlers or perform non-idempotent work before an interrupt without a replay design.
- Checkpoints can retain prompts, credentials accidentally placed in state, and tool outputs; store only needed data with access and retention controls.
- Graph persistence does not supply a scheduler or prove that a stopped worker will wake up.

## Official Skills

Upstream: [langchain-ai/langchain-skills](https://github.com/langchain-ai/langchain-skills). Select `langgraph-fundamentals`, `langgraph-persistence`, and `langgraph-human-in-the-loop` as needed; use `langgraph-cli` only for that deployment workflow. Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) to review and install only the needed project-scoped selection.

## Documentation

- [Overview](https://docs.langchain.com/oss/python/langgraph/overview) · [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) · [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- Releases: [LangGraph](https://github.com/langchain-ai/langgraph/releases) · [changelog](https://changelog.langchain.com/)
