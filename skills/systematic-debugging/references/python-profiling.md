# Python Profiling

Use profiling to locate a measured slowdown; [benchmark](../../benchmark/SKILL.md) owns uninstrumented before/after comparisons. Start with the installed Python standard library, run through `uv`, and use a representative, bounded workload in an isolated workspace.

1. Compare elapsed and CPU time for the same work. High elapsed time with little CPU suggests waiting; high CPU suggests computation, but process totals can include other threads and exclude child processes.
1. For CPU/call attribution, substitute the real script and arguments below. Create the scratch output directory first and keep input, revision, runtime, and cache state with the result.

   ```bash
   uv run python -m cProfile -o .agents/tmp/workload.prof workload.py
   uv run python -c 'import pstats; pstats.Stats(".agents/tmp/workload.prof").strip_dirs().sort_stats("cumulative").print_stats(20)'
   ```

1. Read cumulative time to find expensive call paths, then self time and call counts to distinguish expensive work from repeated small work. Do not treat profiler timing as an unbiased benchmark or assume the main-thread profile covers workers or async task causality.
1. For Python allocation growth, start tracing before the workload, warm it up, take a baseline snapshot, execute a bounded repeated batch, then compare snapshots and current/peak traced memory. Release expected temporary state before deciding something leaks.

   ```python
   import tracemalloc

   tracemalloc.start(10)
   # Warm up the actual workload before this baseline.
   before = tracemalloc.take_snapshot()
   # Run a bounded batch here, then release expected temporary state.
   after = tracemalloc.take_snapshot()
   for change in after.compare_to(before, "lineno")[:10]:
       print(change)
   print(tracemalloc.get_traced_memory())
   tracemalloc.stop()
   ```

1. If process memory grows without traced allocation growth, investigate native buffers, mapped files, child processes, and allocator retention. `tracemalloc` is not a complete process-memory measurement.
1. For blocked I/O, record elapsed spans around the actual file/network/lock boundaries with redacted inputs and bounded timeouts. Use stack snapshots in a disposable reproduction when necessary; never infer the cause solely from a high cumulative-time parent function.
1. State one bottleneck hypothesis, change only that cause when authorized, and rerun the same uninstrumented workload plus correctness tests. Remove temporary instrumentation unless it has an ongoing owner.

Profiles can reveal source paths and workload details. Keep them private by default and read only trusted profile files; profiler artifacts are not a safe interchange format for untrusted uploads.

Sources: [Python profiling](https://docs.python.org/3/library/profile.html), [tracemalloc](https://docs.python.org/3/library/tracemalloc.html), and [time clocks](https://docs.python.org/3/library/time.html).
