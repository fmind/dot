---
name: benchmark
description: "Benchmark commands with hyperfine and HTTP load with oha or Locust against a same-session baseline."
---

# Benchmark

Produce comparable measurements for a stated performance question: hyperfine answers "how long does this command take", oha "how does this endpoint behave under simple load", and Locust "how does the service hold up under realistic concurrent users". The parent [skill](../SKILL.md) owns diagnosing why something is slow, and [Python profiling](python-profiling.md) locates the hot path.

## Tools

- **hyperfine is global**: the workstation installs it for every project.
- **Declare oha and Locust in the project**: add oha to the project's `mise.toml` with `mise use --pin oha` per [mise](../../mise/SKILL.md), and Locust as a development dependency with `uv add --dev locust`, then commit the updated locks. Run them from the project root (`mise exec -- oha ...` when the shell has no mise activation).

## Workflow

1. **Confirm authority**: never load-test a remote service you do not own or a production system without explicit approval; agree a load bound and stop condition appropriate to the target's capacity.
1. **Measure with the matching section below**: use at least 3 warmup runs and 10 measured runs for commands and at least 30 seconds for endpoints, and compare against a baseline measured the same way in the same session.
1. **Quantify uncertainty**: compare repeated, equivalently controlled runs and report uncertainty in the difference; a run's standard deviation alone does not decide significance. Alternate baseline and candidate measurements when machine drift matters.
1. **Report**: the command lines, the exported table, the relative change, and the conditions. Keep the raw export (`bench.json`, `oha.json`, or Locust CSV) when the number will be tracked over time.

## Commands and HTTP endpoints

```bash
hyperfine --warmup 3 --runs 10 'old-cmd' 'new-cmd'                       # A/B with mean ± σ and a relative speed line
hyperfine --warmup 3 --prepare 'uv sync --frozen' 'uv run --frozen pytest -q'   # measure the test run, not uv's lock check
hyperfine --parameter-list n 10,100,1000 'tool --items {n}'               # scaling curve
hyperfine --export-markdown bench.md --export-json bench.json 'cmd'       # tables for the PR, raw data for later
oha -z 30s -c 50 -q 100 --latency-correction http://localhost:8080/health # 30 s, 50 connections, target 100 requests/s; adapt to the authorized load
oha -n 2000 -c 20 -m POST -H 'Content-Type: application/json' -d '{"q":1}' http://localhost:8080/api
oha --no-tui -z 10s -c 10 --output-format json -o oha.json http://localhost:8080/   # scriptable output for CI or a report
```

## Concurrent user scenarios with Locust

1. **Establish the authorized envelope**: the target, environment, test accounts, user cap, spawn rate, duration, and stop thresholds. Default fixture examples to loopback; a real load test needs authority for its traffic and writes.
1. **Write the locustfile**: define an `HttpUser` with `@task` methods and a realistic `wait_time`; use `self.client` so requests enter Locust statistics.
1. **Name requests and check business success**: group dynamic URLs with stable request names and check business success with `catch_response=True`. Prepare test data and cleanup so repeated users do not corrupt one another's state.
1. **Start with a tiny local smoke** against an already running fixture service:
   ```bash
   uv run locust -f locustfile.py --headless --host http://127.0.0.1:8000 --users 2 --spawn-rate 1 --run-time 10s --stop-timeout 5 --csv smoke --html smoke.html --exit-code-on-error 1
   ```
1. **Increase load only within the agreed envelope**: observe latency percentiles, throughput, errors, server saturation, and generator CPU and network capacity together.
1. **Gate the run on acceptance thresholds**: encode latency and failure-ratio thresholds in the run's exit status; `--exit-code-on-error` alone does not enforce a latency SLO. Verify the gate with an intentionally failing local response.

## Gotchas

- **Localhost numbers exclude the network**: oha against `localhost` measures the server, not the user experience.
- **Correction needs a rate**: oha ignores `--latency-correction` without `-q`; set an authorized request rate and report that rate, concurrency, and achieved throughput together.
- **hyperfine 2 runs without a shell**: commands no longer pay shell startup; add `-S` (the platform shell) or `--shell=bash` for pipes, `&&`, globs, or variables. 2.x JSON exports use schema v2, so never compare them with 1.x results.
- **Caches lie**: a second run of a build or query hits caches; use `--prepare` to clear them when the cold path is what matters.
- **Separate Cloud Run cold starts**: benchmark with `--min-instances` known, and separate first-request latency from steady state per the [cloud-run skill](../../cloud-run/SKILL.md).
- **Spawn rate is users per second**: not requests per second; think time and response latency determine Locust's request load.
- **Bound runs and targets**: avoid unbounded runs, accidental production hosts, and real payment or email tasks. Distributed Locust workers multiply the available traffic capacity.

## Documentation

- [hyperfine](https://github.com/sharkdp/hyperfine) · [oha](https://github.com/hatoo/oha) · [Writing a locustfile](https://docs.locust.io/en/stable/writing-a-locustfile.html) · [Headless runs and exit codes](https://docs.locust.io/en/stable/running-without-web-ui.html)
- Releases: [hyperfine](https://github.com/sharkdp/hyperfine/releases) · [oha](https://github.com/hatoo/oha/releases) · [Locust changelog](https://docs.locust.io/en/stable/changelog.html)
- Official skills: none found in [locustio/locust](https://github.com/locustio/locust) on 2026-10-04; community packages are not upstream endorsements.
- Companion skills: [quality-assurance](../../quality-assurance/SKILL.md) (performance as part of a test campaign), [production-readiness](../../production-readiness/SKILL.md) (capacity evidence before promotion).
