---
name: locust
description: Load-test HTTP services with Locust. Use for user journeys, spawn rates, headless runs, latency thresholds, and distributed load generation.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/locust
  created: "2026-09-10"
  updated: "2026-09-11"
---

# Locust

Use Locust for concurrent user behavior and service capacity tests; [benchmark](../benchmark/SKILL.md) owns simple HTTP/command benchmarks.

## Workflow

1. Establish the authorized target, environment, test accounts, user cap, spawn rate, duration, and stop thresholds. Default fixture examples to loopback; a real load test needs authority for its traffic and writes.
1. Add `locust` with `uv add --dev locust`. Define an `HttpUser` with `@task` methods and realistic `wait_time`; use `self.client` so requests enter Locust statistics.
1. Group dynamic URLs with stable request names and check business success using `catch_response=True`. Prepare test data and cleanup so repeated users do not corrupt one another's state.
1. Start with a tiny local smoke against an already running fixture service:
   ```bash
   uv run locust -f locustfile.py --headless --host http://127.0.0.1:8000 --users 2 --spawn-rate 1 --run-time 10s --stop-timeout 5 --csv smoke --html smoke.html --exit-code-on-error 1
   ```
1. Increase load only within the agreed envelope. Observe latency percentiles, throughput, errors, server saturation, and generator CPU/network capacity together.
1. Encode acceptance thresholds in the run's exit status, including latency and failure ratio; `--exit-code-on-error` alone does not enforce a latency SLO. Verify the gate with an intentionally failing local response.

## Gotchas

- Spawn rate is users per second, not requests per second; think time and response latency determine request load.
- Avoid unbounded runs, accidental production hosts, and real payment/email tasks. Distributed workers multiply the available traffic capacity.
- Keep user sessions and credentials isolated. A saturated generator understates server capacity and makes results unreliable.

## Official Skills

No consumer Agent Skill was found in the inspected [locustio/locust](https://github.com/locustio/locust) repository on 2026-09-10. Use the official documentation below; community packages are not upstream endorsements.

## Documentation

- [Writing a locustfile](https://docs.locust.io/en/stable/writing-a-locustfile.html) · [Headless runs and exit codes](https://docs.locust.io/en/stable/running-without-web-ui.html)
- Releases: [Locust changelog](https://docs.locust.io/en/stable/changelog.html) · [GitHub releases](https://github.com/locustio/locust/releases)
