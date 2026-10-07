# Python Profiling

Locate a measured slowdown with a representative, bounded workload run through `uv`; [benchmark](../../benchmark/SKILL.md) owns uninstrumented before/after comparisons. Add a profiler as a development dependency only for a concrete need; keep captures private (they reveal paths and workload details) and read only trusted profile files.

- **Separate waiting from computation first**: compare elapsed and CPU time for the same work before choosing a tool.
- **Default to Pyinstrument for time**: `uv run pyinstrument -r html -o profile.html workload.py` (or `-m package.module`) gives sampled elapsed-time trees, waits included; choose async attribution deliberately. `python -m cProfile` remains the zero-install fallback, but its timings are biased and miss worker threads.
- **Default to Memray for memory**: `uv run memray run -o capture.bin workload.py`, then `uv run memray stats capture.bin` and `uv run memray flamegraph -o memory.html capture.bin`; add `--native` at capture time when extension allocations matter. Allocation volume is not a leak, and RSS includes allocator arenas and mapped memory; if RSS grows without tracked allocation growth, look at native buffers, mapped files, and child processes.
- **Launch hung processes under py-spy**: attaching with `py-spy dump --pid` needs ptrace, which Yama `ptrace_scope` 1 denies without elevation (out of scope). Launch instead with `uv run --with py-spy py-spy record -o profile.svg --subprocesses -- python workload.py`, or pre-arm `faulthandler.register(signal.SIGUSR1)` to dump stacks on a signal.
- **Change one cause, then remeasure**: rerun the same uninstrumented workload plus correctness tests, and remove temporary instrumentation unless it has an owner.

Sources: [Pyinstrument](https://pyinstrument.readthedocs.io/), [Memray](https://bloomberg.github.io/memray/), [py-spy](https://github.com/benfred/py-spy), [Python profiling](https://docs.python.org/3/library/profile.html).
