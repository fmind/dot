---
name: python-async
description: "Async design, cancellation, timeouts, and shutdown."
---

# Python Async

Use `asyncio` only for concurrent I/O waits; keep CPU work in processes, blocking drivers sync or behind `asyncio.to_thread`, and sequential CLIs/scripts synchronous (keep AnyIO where already chosen; [api-client](../api-client/GUIDE.md) owns HTTP retries).

## Version-specific invariants

- **Exit a `TaskGroup` early via `group.cancel()`** (`Python 3.15+` / `AnyIO 4.14+`) instead of sentinel exceptions.
- **Bound pool queues**: use `Executor.map(fn, items, buffersize=n)` (`3.14+`) for threads/processes, and fixed workers + `asyncio.Queue(maxsize=...)` instead of semaphores over millions of tasks.
- **Use `loop_factory`**: pass to `asyncio.run` / `asyncio.Runner` (`uvloop.run(main())`) and `pytest_asyncio_loop_factories` (`set_event_loop_policy` and `uvloop.install()` warn in `3.14+` and disappear in `3.16`).
- **In-process hung-loop dump**: register `SIGUSR1` calling `asyncio.print_call_graph(task, file=sys.stderr)` over `asyncio.all_tasks()` (`3.14+`), avoiding ptrace-blocked `python -m asyncio pstree <pid>` ([performance](../performance.md)).
- **AnyIO shields & worker threads**: `fail_after`/`move_on_after` use sync `with` (shield async cleanup via `with anyio.move_on_after(sec, shield=True):`, then re-raise cancellation). Cancelling `to_thread` never stops the thread — pass an explicit stop event and join within shutdown grace.
- **Retain background task refs**: store detached `create_task` handles in a `set` (`task.add_done_callback(tasks.discard)`) so GC cannot collect them mid-flight.

## Documentation

- [Asyncio tasks](https://docs.python.org/3/library/asyncio-task.html) · [AnyIO cancellation](https://anyio.readthedocs.io/en/stable/cancellation.html) · [AnyIO threads](https://anyio.readthedocs.io/en/stable/threads.html) · [CPython changelog](https://docs.python.org/3/whatsnew/changelog.html)
