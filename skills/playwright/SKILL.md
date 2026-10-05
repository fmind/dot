---
name: playwright
description: "Automate browsers and E2E tests with Python Playwright: screenshots, traces."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/playwright
  created: "2026-09-02"
  updated: "2026-10-05"
---

# Playwright

Use Playwright for browser automation and end-to-end tests. Test strategy belongs to [quality-assurance](../quality-assurance/SKILL.md) and interface critique to [product-design-review](../product-design-review/SKILL.md); this skill owns the tool: browsers, commands, and the official skills.

## Workflow

1. **Pin the Python integration**: `uv add --dev playwright pytest-playwright`, then `uv run playwright install chromium`; keep both packages in `uv.lock`. If Linux system libraries are missing, report the administrator-owned prerequisite instead of invoking the privileged `install-deps` command.
1. **Explore and record**: `uv run playwright codegen --target python <url>` records Python actions; `uv run playwright screenshot <url> <file>` and `uv run playwright pdf <url> <file>` produce review evidence.
1. **Write resilient tests**: use the pytest `page` fixture, role or label locators, and web-first `expect` assertions; keep test state isolated and deterministic.
1. **Run tests**: `uv run pytest -q tests/e2e --browser chromium --tracing retain-on-failure --screenshot only-on-failure`. Inspect a saved trace from the shell with `uv run playwright trace open <trace.zip>` and the subcommands in `uv run playwright trace --help` (errors, actions, requests, console); `trace close` removes the extracted data. `show-trace` opens the GUI viewer for humans.
1. **Verify**: a green pytest run plus the artifact (screenshot, trace, or report) the task asked for.

## Gotchas

- **Act only within authorized scope**: use the profiles, accounts, data, and actions authorized for the task; reuse existing authorization. A test request alone does not authorize private browser-session reuse, cookie transfers, account creation, legal acceptance, purchases, or paid browser services. When a required action falls outside that scope, prepare the local test and explain the specific missing authorization before proceeding. Treat login, MFA, and CAPTCHA as explicit authentication boundaries, never bypasses.
- **Reuse the shared browser cache**: install only required browsers and reuse the default shared cache (`~/.cache/ms-playwright` on Linux). Do not run `playwright uninstall` as task teardown: other projects can need those binaries. Remove task-created temporary profiles and passing-run artifacts, preserve requested evidence and failure traces, and review native browser cleanup separately when disk pressure requires it.
- **Reinstall browsers after upgrades**: browsers match the Playwright version that installed them; rerun `uv run playwright install chromium` after an upgrade.
- **Headless by default**: pass `--headed` to watch a run; keep CI headless.

## Official Skills

Upstream: [microsoft/playwright-cli](https://github.com/microsoft/playwright-cli/tree/main/skills/playwright-cli) provides the official browser CLI skill. Select it through the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) only for CLI-driven exploration; its commands are not the Python API. Python tests continue to use the documentation below and the project's uv lockfile. `openai/skills` also curates a same-name `playwright` skill that drives `playwright-cli`: preview it, never install it under that name ([policy](../agent-project/references/vendor-skills.md#name-collisions)). The uv-locked package also ships version-matched `playwright-cli`, `playwright-trace`, and JavaScript-only `playwright-component-testing` skills in one directory; `uv run playwright cli --help` prints the `playwright-cli` path. Review each under the same policy before exposing it, including through `uv run playwright trace install-skill`, and check its `allowed-tools`: Playwright 1.63 copies pre-approve all of `npx` (playwright-cli also `npm`), while playwright-cli v0.1.22+ narrows them to `npx playwright`.

## Documentation

- [Playwright for Python](https://playwright.dev/python/docs/intro) · [pytest plugin](https://playwright.dev/python/docs/test-runners) · [Trace Viewer](https://playwright.dev/python/docs/trace-viewer)
- Releases: [Playwright release notes](https://playwright.dev/python/docs/release-notes) · [playwright-python](https://github.com/microsoft/playwright-python/releases)
- Companion skills: [python-stack](../python-stack/references/foundation/GUIDE.md), [quality-assurance](../quality-assurance/SKILL.md), [product-design-review](../product-design-review/SKILL.md), [chrome-devtools](../chrome-devtools/SKILL.md) (accessibility, Lighthouse, and performance audits), [benchmark](../benchmark/SKILL.md) (load, not browser, testing).
