---
name: python-async
description: "Async design, cancellation, timeouts, and shutdown."
---

# Python Async

Own concurrent task lifetime and failure behavior. Async pays off only when many operations wait on IO at the same time; reject it for CPU-bound work (use processes), behind a blocking driver (stay synchronous or `asyncio.to_thread`), and in sequential scripts and CLIs. [api-client](../../../api-client/SKILL.md) owns HTTP semantics and retries, framework skills own application integration.

## Workflow

1. **Prefer the existing runtime, else asyncio**: inspect the supported Python versions, event-loop owner, async libraries, and pytest plugins. Preserve an existing AnyIO convention; otherwise use standard-library asyncio without adding a runtime dependency. Use `uv` for project execution and required test dependencies.
1. **Bound admission as well as active work**: for large or streaming inputs, use a fixed worker count and bounded queue so producers wait for capacity; a semaphore around millions of created tasks still leaves millions of task objects.
1. **Clean up, then propagate cancellation**: release resources with context managers or `try/finally`, and propagate cancellation after cleanup. Use [cancellation and tests](references/cancellation.md) for asyncio/AnyIO differences, bounded cleanup, and deterministic failure probes.
1. **Move blocking IO to threads**: use the project's thread facility. A cancelled await does not forcibly stop its worker thread; use cooperative termination or an explicitly managed process when termination is required. Choose a process executor for CPU work only after checking workload and serialization costs.
1. **Dump a hung process's task tree**: `python -m asyncio pstree <pid>` on Python 3.14+; attaching needs elevated debugger privileges on the target.

## Gotchas

- **Do not swap `gather` and TaskGroup blindly**: `gather` does not provide TaskGroup's sibling-cancellation behavior on ordinary child failure. Preserve deliberate partial-result semantics instead of mechanically replacing either API.
- **Hold references to detached tasks**: detached tasks need a lifecycle owner, exception observation, and shutdown handling. The loop keeps only weak references, so hold each task in a set until it completes; an unreferenced task can be collected mid-flight. Request-local background work is not a durable job queue.
- **Keep scopes and sessions task-local**: keep AnyIO cancel scopes nested in the same task. A task's database session belongs to that task; async does not make shared mutable state safe.

## Documentation

- [Asyncio tasks and cancellation](https://docs.python.org/3/library/asyncio-task.html) · [Queues](https://docs.python.org/3/library/asyncio-queue.html) · [AnyIO cancellation](https://anyio.readthedocs.io/en/stable/cancellation.html) · [AnyIO worker threads](https://anyio.readthedocs.io/en/stable/threads.html)
- Releases: [CPython changelog](https://docs.python.org/3/whatsnew/changelog.html)
