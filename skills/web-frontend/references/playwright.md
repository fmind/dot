---
name: playwright
description: "Automate browsers/E2E tests via Playwright: screenshots, traces."
---

# Playwright

Browser automation and E2E testing ([python/testing](../../python/references/testing/GUIDE.md) owns test structure and fixtures).

## Workflow

1. **Match tool to surface**: use [xh](../../full-review/references/http-probing.md) for pure HTTP/JSON diagnostics; whenever UI rendering, visual layout, responsive viewports, interactive state transitions (empty, loading, error, populated), or accessibility matter, verify in a real browser targeting semantic roles/labels and asserting state after every action.
1. **Pin Python packages**: `uv add --dev playwright pytest-playwright` (`uv.lock`), then `uv run playwright install chromium`. Report missing OS libraries instead of running privileged `install-deps`.
1. **Record and capture**: `uv run playwright codegen --target python-pytest <url>`, `uv run playwright screenshot --viewport-size=1440,900 --full-page <url> <desktop.png>`, `uv run playwright screenshot --viewport-size=390,844 --full-page <url> <mobile.png>` (always read the captured PNGs visually to inspect layout, wrapping, and contrast), and `uv run playwright pdf <url> <file>`. Outside projects that lock Playwright, run `uvx --from playwright==<version> playwright` (installing `chromium` first) instead of polluting `pyproject.toml`.
1. **Wire opt-in `test:e2e` and run**: keep default `test` filtering `-m "not integration and not e2e"`. Add `[tasks."test:e2e"]` running `uv run --locked pytest -q -m e2e --browser chromium --tracing retain-on-failure --screenshot only-on-failure --timeout=120`, and serve the ASGI app on an ephemeral `127.0.0.1:0` loopback socket inside a `tests/e2e/conftest.py` thread/uvicorn-free Granian fixture. Inspect traces via `uv run playwright trace open <trace.zip>`, `trace --help` subcommands, and `trace close` (`show-trace` opens the GUI). For live CLI debugging, run one test with `--playwright-debug=cli -s`, attach via `uv run playwright cli attach <session>`, then stop and remove `.playwright-cli/`.

## Gotchas

- **Respect authorization boundaries**: testing never authorizes reusing personal browser profiles/cookies, creating accounts, accepting terms, hitting staging/prod unapproved, or bypassing login/MFA/CAPTCHA.
- **Share `~/.cache/ms-playwright`**: install only needed browsers and never run `playwright uninstall` in teardown (other projects share the cache); clean up only temp profiles and passing-run artifacts.
- **Reinstall after version bumps**: rerun `uv run playwright install chromium` whenever Playwright upgrades.
- **CLI Lighthouse & live deploy smokes**: for automated CWV/a11y budgets in `mise` tasks, pin `npm:lighthouse` beside Playwright and run both against ephemeral local servers (`test:lighthouse:local`) and post-deploy URLs (`test:deployed`).

## Official Skills

Upstream `microsoft/playwright-cli` (`playwright-cli` only; collides with `openai/skills` `playwright` — see [vendor-skill policy](../../agent-harnesses/references/vendor-skills.md#name-collisions)). Audit `allowed-tools` on bundled CLI skills (`playwright <1.64` and `playwright-cli <0.1.22` pre-approve broad `npx`/`npm`).

## Documentation

- [Playwright for Python](https://playwright.dev/python/docs/intro) · [pytest plugin](https://playwright.dev/python/docs/test-runners) · [Trace Viewer](https://playwright.dev/python/docs/trace-viewer)
- Releases: [Playwright release notes](https://playwright.dev/python/docs/release-notes) · [playwright-python](https://github.com/microsoft/playwright-python/releases)
- Companion skills: [python/foundation](../../python/references/foundation/GUIDE.md), [chrome-devtools](chrome-devtools.md) (accessibility, Lighthouse, and performance audits), [performance](../../python/references/performance.md) (load, not browser, testing).
