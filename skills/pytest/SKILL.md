---
name: pytest
description: Write and run Python tests with pytest. Use for fixtures, parametrization, monkeypatching, exception checks, collection, and Hypothesis integration.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/pytest
  created: "2026-09-10"
  updated: "2026-09-10"
---

# pytest

Use pytest for deterministic Python behavior tests; [test-driven-development](../test-driven-development/SKILL.md) owns red/green implementation and [quality-assurance](../quality-assurance/SKILL.md) owns broader test campaigns.

## Workflow

1. Inspect pytest configuration, fixtures, plugins, and the repository's canonical test task. Add `pytest` with `uv add --dev pytest` only when missing; keep plugin dependencies explicit.
1. Confirm collection with `uv run pytest --collect-only -q <tests-path>`. Run a focused case with `uv run pytest -q <path>::<test-name>` before broadening to the affected suite.
1. Test observable outputs and failure behavior using small inputs, `tmp_path`, `monkeypatch`, and `capsys`/`caplog` as appropriate. Patch the name where the code under test looks it up.
1. Use parametrization for meaningful input partitions and `pytest.raises(..., match=...)` around only the expected failing operation. Give fixtures the narrowest practical scope and deterministic teardown.
1. Keep network, clock, randomness, environment, and filesystem state controlled. Use the project's async plugin or runner convention; do not assume pytest runs async tests by itself.
1. For generated input coverage, follow the existing [Hypothesis property tests](../test-driven-development/references/property-tests.md) guide for strategies, independent invariants, shrinking, state machines, and failure replay. Use it selectively; ordinary examples remain the public contract.
1. Run the native gate and inspect warnings, skips, and collection count. Add xdist or coverage only when the project needs them; verify worker isolation before parallel execution.

## Gotchas

- Exit code 5 means no tests were collected; it is not success. Deselection and unexpectedly skipped tests can leave behavior unverified.
- Autouse/session fixtures can hide dependencies and leak state. Use `yield` teardown or context managers for resources.
- A function-scoped fixture is not recreated for each Hypothesis example. Reset mutable state per example and keep health checks active; [python-async](../python-async/SKILL.md) owns concurrent task and cancellation behavior.
- Register custom markers and use strict marker/config validation where appropriate; never turn a regression into a skip or blanket warning filter.

## Official Skills

No consumer Agent Skill was found in the inspected [pytest-dev/pytest](https://github.com/pytest-dev/pytest) repository on 2026-09-10. Use the official documentation below; community packages are not upstream endorsements.

## Documentation

- [Invocation](https://docs.pytest.org/en/stable/how-to/usage.html) · [Fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html) · [Good practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html)
