# Cancellation and Tests

For asyncio on Python 3.11+, put related tasks inside a `TaskGroup` and the operation inside `asyncio.timeout`. A non-cancellation child failure cancels siblings and is normally raised as an exception group after they finish. Catch only errors the boundary can handle; do not turn an exception group into an empty successful result.

Use `try/finally` for resource release. If explicitly catching `asyncio.CancelledError`, re-raise it after cleanup. Cleanup can itself be interrupted by a later cancellation; a required asynchronous finalizer needs an owned task, a bounded wait, and a defined failure outcome. `asyncio.shield` alone does not make the caller wait for completion or impose a timeout.

AnyIO uses level cancellation: await points inside an effectively cancelled scope can raise cancellation repeatedly. For asynchronous cleanup, use a short shielded scope such as `with anyio.move_on_after(cleanup_seconds, shield=True):`, then propagate the original cancellation. Check whether cleanup completed and report exhaustion according to the resource contract. AnyIO's `fail_after` and `move_on_after` use synchronous `with`, not `async with`.

Cancelling `asyncio.to_thread` does not kill its underlying thread. AnyIO's thread API likewise requires deliberate waiting or abandonment semantics; abandoned work can still mutate resources. Give cooperative workers a stop signal and join them within the owner's shutdown policy. Do not report termination merely because the await ended.

Use events or barriers to establish test ordering rather than short sleeps. A synchronous pytest test can call `asyncio.run` when no loop is already running; async fixtures should use the project's existing plugin instead.

```python
import asyncio

import pytest


def test_child_failure_cleans_up_sibling():
    async def scenario():
        started = asyncio.Event()
        cleaned = asyncio.Event()

        async def sibling():
            try:
                started.set()
                await asyncio.Event().wait()
            finally:
                cleaned.set()

        async def failing_child():
            await started.wait()
            raise ValueError("invalid record")

        async with asyncio.timeout(5):
            with pytest.raises(ExceptionGroup) as failure:
                async with asyncio.TaskGroup() as group:
                    worker = group.create_task(sibling())
                    group.create_task(failing_child())
            assert len(failure.value.exceptions) == 1
            assert isinstance(failure.value.exceptions[0], ValueError)
            assert worker.cancelled()
            assert cleaned.is_set()

    asyncio.run(scenario())
```

The timeout bounds a hung fixture; events establish the ordering. Also exercise external cancellation after acquisition, timeout while waiting for queue capacity, and graceful shutdown. Assert producer admission stops, owned tasks are awaited, and resource cleanup occurs. Bound queued items and bytes where payload sizes vary; a maximum item count alone does not bound memory.

Sources: [Python tasks](https://docs.python.org/3/library/asyncio-task.html), [AnyIO cancellation](https://anyio.readthedocs.io/en/stable/cancellation.html), and [worker threads](https://anyio.readthedocs.io/en/stable/threads.html).
