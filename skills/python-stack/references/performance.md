---
name: performance
description: "Profile Python CPU and memory, and benchmark commands and HTTP load with hyperfine, oha, or Locust."
---

# Performance

Measure against a same-session baseline first (`hyperfine` for CLIs, `oha` for single endpoints, `locust` for multi-user flows), then profile hot paths.

## Benchmarks

- **Tool pins & authority**: `hyperfine` is workstation-global; pin `oha` per project (`mise use --pin oha`, [mise](../../mise/SKILL.md)) and `locust` via `uv add --dev locust`. Never load-test unowned targets or production without explicit approval (bound rate, duration, and worker count).
- **Method**: >=3 warmups and >=10 runs (or >=30s load); keep changes only when gains beat variance with green tests, recording reverted attempts.

```bash
hyperfine --warmup 3 --runs 10 'old-cmd' 'new-cmd'
hyperfine --warmup 3 --prepare 'uv sync --frozen' --export-markdown bench.md --export-json bench.json 'uv run --frozen pytest -q'
oha --no-tui -z 30s -c 50 -q 100 --latency-correction --output-format json -o oha.json http://localhost:8080/health
uv run locust -f locustfile.py --headless --host http://127.0.0.1:8000 --users 2 --spawn-rate 1 --run-time 10s --stop-timeout 5 --csv smoke --exit-code-on-error 1
```

## Benchmark gotchas

- **`hyperfine 2.x`**: runs shell-less by default — pass `-S` / `--shell=bash` for pipes/`&&`/globs/`$VAR`, and `--env 'NAME=value'` instead of inline `NAME=value` prefixes (schema v2 JSON is incompatible with `1.x`).
- **`oha`**: counts `4xx`/`5xx`/unfollowed `3xx` (`--redirect 0` default since `1.15`) as HTTP responses and exits `0` — inspect `statusCodeDistribution` in JSON; `--latency-correction` requires `-q`.
- **`locust` & Cloud Run**: `--exit-code-on-error` checks errors, not latency SLOs (validate business responses via `catch_response=True`); separate Cloud Run cold starts from steady state with known `--min-instances` ([cloud-run](../../cloud-run/SKILL.md)).

## Python profiling

Keep captures private (contain paths/data) and open only trusted profile files:

- **Time**: compare wall vs CPU first. Default to `uv run pyinstrument -r html -o profile.html workload.py` (wall time + waits). On Python `3.15+`, stdlib `uv run python -m profiling.sampling run --flamegraph -o profile.html workload.py` needs zero deps (`--mode cpu`, `-a`, `--async-aware`, `--subprocesses`, `--diff-flamegraph base.bin` vs `--binary -o base.bin`; `<3.15` `cProfile` misses threads and biases fast calls).
- **Memory**: `uv run memray run -o capture.bin workload.py` (`--native` for C/Rust extensions) -> `memray stats` / `memray flamegraph --confidential-files=all -o memory.html capture.bin` (untracked RSS growth indicates native buffers, `mmap`, or child processes).
- **Ptrace-restricted hosts & headless state**: when Linux Yama `ptrace_scope >= 1` blocks PID attach (`py-spy`, `profiling.sampling attach`, `pdb -p`, `asyncio pstree`, `sys.remote_exec`), spawn as parent at scope 1 (`uv run --with 'py-spy>=0.4.3' py-spy record -o profile.svg --subprocesses -- python workload.py`) or pre-arm `faulthandler.register(signal.SIGUSR1)` on scope 2/3 or macOS. Inspect failing locals via `uv run --locked pytest -x -l --lf <path>` or `uv run python -m pdb -c continue -c 'p <expr>' -c quit script.py < /dev/null` (note `pdb` exits `0` even after an exception).

## Documentation

- [hyperfine](https://github.com/sharkdp/hyperfine) ([releases](https://github.com/sharkdp/hyperfine/releases)) · [oha](https://github.com/hatoo/oha) ([releases](https://github.com/hatoo/oha/releases)) · [Locust](https://docs.locust.io/en/stable/running-without-web-ui.html) ([releases](https://github.com/locustio/locust/releases)) · [Pyinstrument](https://pyinstrument.readthedocs.io/) · [Memray](https://bloomberg.github.io/memray/) ([releases](https://github.com/bloomberg/memray/releases)) · [py-spy](https://github.com/benfred/py-spy) ([releases](https://github.com/benfred/py-spy/releases)) · [Python profiling](https://docs.python.org/3/library/profiling.html).
