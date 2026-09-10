---
name: python-async
description: Implement Python async concurrency. Use for task groups, cancellation, deadlines, bounded queues, blocking work, and graceful shutdown in asyncio or AnyIO.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/python-async
  created: "2026-09-10"
  updated: "2026-09-10"
---

# Python Async

Own concurrent task lifetime and failure behavior. [api-client](../api-client/SKILL.md) owns HTTP semantics and retries, [sqlalchemy](../sqlalchemy/SKILL.md) owns database sessions, and framework skills own application integration.

## Workflow

1. Inspect the supported Python versions, event-loop owner, async libraries, and pytest plugins. Preserve an existing AnyIO convention; otherwise use standard-library asyncio without adding a runtime dependency. Use `uv` for project execution and required test dependencies.
1. Define which parent owns each task, when work completes, how failures propagate, and what must finish during shutdown. Keep `asyncio.run` at a synchronous entry point; use the existing loop inside servers and notebooks.
1. Use `asyncio.TaskGroup` on Python 3.11+ or the project's AnyIO task group for related work. Let the parent await completion and observe failures; inspect supported APIs before applying examples to older Python versions.
1. Bound admission as well as active work. For large or streaming inputs, use a fixed worker count and bounded queue so producers wait for capacity; a semaphore around millions of created tasks still leaves millions of task objects.
1. Apply an operation deadline around all its work, including waiting for capacity and retries. Use `asyncio.timeout`/`timeout_at` or AnyIO `fail_after` according to the existing runtime; keep transport timeouts separate and test their interaction.
1. Release resources with context managers or `try/finally`, and propagate cancellation after cleanup. Use [cancellation and tests](references/cancellation.md) for asyncio/AnyIO differences, bounded cleanup, and deterministic failure probes.
1. Move blocking IO to the project's thread facility. A cancelled await does not forcibly stop its worker thread; use cooperative termination or an explicitly managed process when termination is required. Choose a process executor for CPU work only after checking workload and serialization costs.
1. Test success, sibling failure, external cancellation, deadline expiry, producer backpressure, and shutdown with in-flight work. Assert resources close and owned tasks finish; use the existing pytest runner and native gate.

## Gotchas

- `gather` does not provide TaskGroup's sibling-cancellation behavior on ordinary child failure. Preserve deliberate partial-result semantics instead of mechanically replacing either API.
- Cancellation is cooperative: blocking calls, long code without await points, and swallowed cancellation can defeat deadlines. Timeout exit may include cleanup time; it is not a hard process kill.
- Detached tasks need a lifecycle owner, exception observation, and shutdown handling. Request-local background work is not a durable job queue.
- Keep AnyIO cancel scopes nested in the same task. A task's database session belongs to that task; async does not make shared mutable state safe.

## Documentation

- [Asyncio tasks and cancellation](https://docs.python.org/3/library/asyncio-task.html) · [Queues](https://docs.python.org/3/library/asyncio-queue.html) · [AnyIO cancellation](https://anyio.readthedocs.io/en/stable/cancellation.html) · [AnyIO worker threads](https://anyio.readthedocs.io/en/stable/threads.html)
