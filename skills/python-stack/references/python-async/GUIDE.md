---
name: python-async
description: "Async design, cancellation, timeouts, and shutdown."
---

# Python Async

Use async only when many operations wait on IO at the same time; keep CPU-bound work in processes, blocking drivers synchronous or behind `asyncio.to_thread`, and sequential scripts and CLIs synchronous. Preserve an existing AnyIO convention; otherwise use standard-library asyncio. [api-client](../api-client/GUIDE.md) owns HTTP semantics and retries.

## Version-specific facts

- **Stop a TaskGroup with `group.cancel()`**: Python 3.15+ and AnyIO 4.14+ let a group exit cleanly once its goal is met, instead of raising and suppressing a sentinel exception.
- **Bound pool submissions with `buffersize`**: `Executor.map(fn, items, buffersize=n)` (3.14+) bounds pending thread or process submissions without a hand-written queue; for asyncio, use a fixed worker count and a bounded queue rather than a semaphore around millions of tasks.
- **Select event loops with `loop_factory`**: pass it to `asyncio.run` or `asyncio.Runner` (uvloop: `uvloop.run(main())`), and use pytest-asyncio's `pytest_asyncio_loop_factories` hook in tests. The policy API, including `set_event_loop_policy` and `uvloop.install()`, warns since Python 3.14 and is removed in 3.16.
- **Dump a hung loop in-process**: pre-arm `loop.add_signal_handler(signal.SIGUSR1, dump)`, where `dump` calls `asyncio.print_call_graph(task, file=sys.stderr)` for each `asyncio.all_tasks()` (3.14+). `python -m asyncio pstree <pid>` needs ptrace, which the host may deny ([performance](../performance.md)).
- **AnyIO shields are synchronous**: `fail_after` and `move_on_after` use `with`, not `async with`. For async cleanup under AnyIO's level cancellation, use `with anyio.move_on_after(cleanup_seconds, shield=True):`, then propagate the original cancellation.
- **Cancelled threads keep running**: cancelling `asyncio.to_thread` or AnyIO's thread call does not stop the worker; give it a stop signal and join it within the shutdown policy before reporting termination.
- **Hold references to detached tasks**: the loop keeps only weak references, so an unreferenced task can be collected mid-flight; keep each in a set until it completes.

## Documentation

- [Asyncio tasks and cancellation](https://docs.python.org/3/library/asyncio-task.html) · [AnyIO cancellation](https://anyio.readthedocs.io/en/stable/cancellation.html) · [AnyIO worker threads](https://anyio.readthedocs.io/en/stable/threads.html)
- Releases: [CPython changelog](https://docs.python.org/3/whatsnew/changelog.html)
