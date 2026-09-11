# pytest Mechanics

Use the project's existing pytest configuration and canonical test task; [python-stack](../../python-stack/SKILL.md) owns the shared configuration baseline. For test-only maintenance, follow this guide without claiming a test-first implementation cycle.

1. Inspect collection with `uv run pytest --collect-only -q <tests-path>` when discovery is uncertain, then run a focused case with `uv run pytest -q <path>::<test-name>`. Exit code 5 means no tests were collected.
1. Test public outcomes with small inputs, narrow fixtures, `tmp_path`, and captured streams or logs. Patch the name where the code under test looks it up; keep resource teardown explicit with context managers or `yield`.
1. Parametrize meaningful input partitions. Keep only the expected failing operation inside `pytest.raises(..., match=...)` so setup errors cannot satisfy the assertion.
1. Control network, clock, randomness, environment, and filesystem state.
1. For Hypothesis, follow [property tests](property-tests.md). A function-scoped fixture is not recreated for every generated example; reset mutable state per example and preserve health checks.
1. Run the relevant suite and native gate. Inspect warnings, skips, and collection counts; unexpected deselection or skips leave behavior unverified. Keep custom markers registered and configuration strict.

pytest runs no `async def` test on its own. When the project already depends on `anyio` (Litestar, Starlette, FastAPI, HTTPX), set `anyio_mode = "auto"` (anyio 4.11+) and add no test dependency; otherwise add `pytest-asyncio` with `asyncio_mode = "auto"`, whose default `strict` mode requires `@pytest.mark.asyncio` on every async test. Never enable both auto modes; the resulting configuration warning becomes an INTERNALERROR under `filterwarnings = ["error"]`.

Add `pytest-xdist` and run `-n auto` only when serial wall time exceeds roughly ten seconds and is dominated by waiting on subprocesses, fsync, or the network; worker startup makes a small fast suite several times slower. Keep `-n` out of `addopts` so focused runs stay serial: `-n auto --pdb` silently falls back to one process, an explicit `-n <count> --pdb` is a usage error, and `-x` stops only after in-flight tests on other workers finish. A session-scoped fixture is built once per worker, so tests sharing a container, port, path, or module state must be fixed rather than pinned to one worker. Measure coverage with `pytest --cov`; `coverage run -m pytest -n ...` silently reports 0%.

Keep the plugin set small: `pytest-cov` for coverage and `pytest-watcher` for the watch loop. Add no others by reflex: pytest 9 ships subtests natively and ignores an installed `pytest-subtests`, `monkeypatch` with `unittest.mock` replaces `pytest-mock`, and the built-in `faulthandler_timeout` setting replaces `pytest-timeout` (add `faulthandler_exit_on_timeout` to abort rather than only dump tracebacks).

Sources: [pytest fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html), [monkeypatch](https://docs.pytest.org/en/stable/how-to/monkeypatch.html), [assertions](https://docs.pytest.org/en/stable/how-to/assert.html), and [good practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html).
