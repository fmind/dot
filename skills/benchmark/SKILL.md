---
name: benchmark
description: "Benchmark commands and HTTP load with hyperfine, oha, and Locust."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/benchmark
  created: "2026-09-02"
  updated: "2026-10-05"
---

# Benchmark

Produce comparable measurements for a stated performance question. Use hyperfine for commands, oha for simple HTTP load, and Locust for realistic concurrent user scenarios; diagnosing why something is slow belongs to [systematic-debugging](../systematic-debugging/SKILL.md).

## Workflow

1. **Fix the question**: one command or endpoint, one metric (mean latency, p99, requests per second), one hypothesis.
1. **Confirm authority**: never load-test a remote service you do not own or a production system without explicit approval; agree a load bound and stop condition appropriate to the target's capacity.
1. **Control the machine**: close heavy processes, run on AC power, and pin versions; record CPU, OS, and tool versions in the report.
1. **Measure with the matching guide**: read only that guide and its required resources; use at least 3 warmup runs and 10 measured runs for commands and at least 30 seconds for endpoints, and compare against a baseline measured the same way in the same session.
1. **Quantify uncertainty**: compare repeated, equivalently controlled runs and report uncertainty in the difference; a run's standard deviation alone does not decide significance. Alternate baseline/candidate measurements when machine drift matters.
1. **Report**: the command lines, the exported table, the relative change, and the conditions. Keep the raw export (`bench.json`, `oha.json`, or Locust CSV) if the number will be tracked over time.

## Task guides

<!-- guides:start -->

- [command-http](references/command-http.md): Compare command latency with hyperfine or measure HTTP throughput with oha.
- [locust](references/locust.md): Concurrent user scenarios, capacity tests, and acceptance thresholds.

<!-- guides:end -->
