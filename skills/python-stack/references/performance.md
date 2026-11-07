---
name: performance
description: "Profile Python CPU and memory, and benchmark commands and HTTP load with hyperfine, oha, or Locust."
---

# Performance

Answer a stated performance question with a measurement, then locate the hot path. hyperfine times commands, oha applies simple load to one endpoint, Locust simulates realistic concurrent users, and the profilers below locate where time or memory goes.

## Benchmarks

- **Place the tools per project**: hyperfine is global on the workstation. Pin oha in the project with `mise use --pin oha` per [mise](../../mise/SKILL.md) and add Locust with `uv add --dev locust`, then commit the locks. Run them from the project root (`mise exec -- oha ...` when the shell has no mise activation).
- **Load-test only what you own**: never load-test a remote service you do not own, or production without explicit approval; agree the load bound, duration, and stop condition first. Distributed Locust workers multiply the traffic.
- **Compare against a same-session baseline**: use at least 3 warmups and 10 runs per command, or 30 seconds per endpoint. Keep a change only when its gain beats run-to-run variance with tests still green, and record reverted attempts so they are not retried.

```bash
hyperfine --warmup 3 --runs 10 'old-cmd' 'new-cmd'                       # A/B with mean ± σ and a relative speed line
hyperfine --warmup 3 --prepare 'uv sync --frozen' 'uv run --frozen pytest -q'   # time the tests, not uv's lock check
hyperfine --export-markdown bench.md --export-json bench.json 'cmd'       # table for the PR, raw data for tracking
oha -z 30s -c 50 -q 100 --latency-correction http://localhost:8080/health # 30 s, 50 connections, 100 requests/s
oha --no-tui -z 10s -c 10 --output-format json -o oha.json http://localhost:8080/
uv run locust -f locustfile.py --headless --host http://127.0.0.1:8000 --users 2 --spawn-rate 1 --run-time 10s --stop-timeout 5 --csv smoke --exit-code-on-error 1
```

## Benchmark gotchas

- **hyperfine 2 runs without a shell**: commands no longer pay shell startup; add `-S` (the platform shell) or `--shell=bash` for pipes, `&&`, globs, or variables. Pipes and `&&` fail with an error, but globs and `$VAR` pass through literally without one; set variables with `--env 'NAME=value'` instead of a `NAME=value cmd` prefix. 2.x JSON exports use schema v2, so never compare them with 1.x results.
- **oha success means any response**: its success rate counts every HTTP response, including 4xx, 5xx, and unfollowed 3xx (`--redirect` defaults to 0 since 1.15), and the run still exits 0; check `statusCodeDistribution` in the JSON before reporting latency.
- **oha correction needs a rate**: oha ignores `--latency-correction` without `-q`; report the rate, concurrency, and achieved throughput together. Against `localhost` it measures the server, not the user experience.
- **Locust spawn rate is users per second**: think time and response latency set the request rate. `--exit-code-on-error` does not enforce a latency SLO; encode latency and failure-ratio thresholds in the exit status, and check business success with `catch_response=True`.
- **Separate Cloud Run cold starts**: benchmark with `--min-instances` known, and separate first-request latency from steady state per [cloud-run](../../cloud-run/SKILL.md).

## Python profiling

Run a representative, bounded workload through `uv`. Add a profiler as a development dependency only for a concrete need; keep captures private, since they reveal paths and workload details, and read only trusted profile files.

- **Separate waiting from computation first**: compare elapsed and CPU time for the same work before choosing a tool.
- **Default to Pyinstrument for time**: `uv run pyinstrument -r html -o profile.html workload.py` (or `-m package.module`) gives sampled elapsed-time trees, waits included.
- **Use the stdlib sampler on Python 3.15+**: `uv run python -m profiling.sampling run --flamegraph -o profile.html workload.py` needs no dependency; `--mode cpu` drops waits, `-a` samples all threads, `--async-aware` follows asyncio tasks, `--subprocesses` follows workers, and `--diff-flamegraph base.bin` compares against a `--binary -o base.bin` capture. Before 3.15, `python -m cProfile` is the zero-install fallback, but its timings are biased and miss worker threads.
- **Default to Memray for memory**: `uv run memray run -o capture.bin workload.py`, then `uv run memray stats capture.bin` and `uv run memray flamegraph -o memory.html capture.bin`; add `--native` at capture time for extension allocations, and pass `--confidential-files=all` to `memray flamegraph` before sharing a report. RSS growth without tracked allocation growth points at native buffers, mapped files, or child processes.
- **Launch hung processes under a sampler when attach is denied**: attaching with `py-spy dump --pid`, `profiling.sampling attach`, `python -m pdb -p`, `python -m asyncio pstree`, or `sys.remote_exec` (3.14+) needs ptrace, which Linux Yama `ptrace_scope` ≥1 denies. At scope 1 a parent may still trace its child, so launch instead with `uv run --with 'py-spy>=0.4.3' py-spy record -o profile.svg --subprocesses -- python workload.py` (0.4.3 added Python 3.15 support); scope 2 or 3, and macOS, where py-spy always needs root, leave only a pre-armed `faulthandler.register(signal.SIGUSR1)` that dumps stacks on a signal.
- **Inspect state without a TTY**: `uv run --locked pytest -x -l --lf <path>` shows the failing locals. For a script, `uv run python -m pdb -c continue -c 'p <expr>' -c quit script.py < /dev/null` prints post-mortem values; that run exits 0 even when the script raised, so take the verdict from a plain run.

## Documentation

- [hyperfine](https://github.com/sharkdp/hyperfine) · [oha](https://github.com/hatoo/oha) · [Locust headless runs](https://docs.locust.io/en/stable/running-without-web-ui.html) · [Pyinstrument](https://pyinstrument.readthedocs.io/) · [Memray](https://bloomberg.github.io/memray/) · [py-spy](https://github.com/benfred/py-spy) · [Python profilers](https://docs.python.org/3/library/profiling.html)
- Releases: [hyperfine](https://github.com/sharkdp/hyperfine/releases) · [oha](https://github.com/hatoo/oha/releases) · [Locust](https://github.com/locustio/locust/releases) · [py-spy](https://github.com/benfred/py-spy/releases) · [Memray](https://github.com/bloomberg/memray/releases)
