---
name: playwright
description: "Automate browsers and E2E tests with Playwright: screenshots and traces."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/playwright
  created: "2026-09-02"
  updated: "2026-11-14"
---

# Playwright

Browser automation and E2E testing ([python-testing](../python-stack/references/python-testing/GUIDE.md) owns test structure and fixtures).

## Workflow

1. **Check HTTP first**: inspect status, headers, and bodies with [xh](../xh/SKILL.md); open a browser only for rendering, interaction, session state, or accessibility, targeting roles/labels and asserting state after each step.
1. **Pin Python packages**: `uv add --dev playwright pytest-playwright` (`uv.lock`), then `uv run playwright install chromium`. Report missing OS libraries instead of running privileged `install-deps`.
1. **Record and capture**: `uv run playwright codegen --target python-pytest <url>`, `uv run playwright screenshot <url> <file>` (`--viewport-size=390,844`, `--full-page`), and `uv run playwright pdf <url> <file>`. Outside projects that lock Playwright, run `uvx --from playwright==<version> playwright` (installing `chromium` first) instead of polluting `pyproject.toml`.
1. **Run and debug**: `uv run pytest -q tests/e2e --browser chromium --tracing retain-on-failure --screenshot only-on-failure`. Inspect traces in the shell via `uv run playwright trace open <trace.zip>`, `trace --help` subcommands, and `trace close` (`show-trace` opens the GUI). For live CLI debugging, run one test in the background with `--playwright-debug=cli -s`, attach via `uv run playwright cli attach <session>`, then stop the run and remove `.playwright-cli/`.

## Gotchas

- **Respect authorization boundaries**: testing never authorizes reusing personal browser profiles/cookies, creating accounts, accepting terms, hitting staging/prod unapproved, or bypassing login/MFA/CAPTCHA.
- **Share `~/.cache/ms-playwright`**: install only needed browsers and never run `playwright uninstall` in teardown (other projects share the cache); clean up only temp profiles and passing-run artifacts.
- **Reinstall after version bumps**: rerun `uv run playwright install chromium` whenever Playwright upgrades.

## Official Skills

Upstream `microsoft/playwright-cli` (`playwright-cli` only; collides with `openai/skills` `playwright` — see [vendor-skill policy](../agent-project/references/vendor-skills.md#name-collisions)). Audit `allowed-tools` on bundled CLI skills (`playwright <1.64` and `playwright-cli <0.1.22` pre-approve broad `npx`/`npm`).

## Documentation

- [Playwright for Python](https://playwright.dev/python/docs/intro) · [pytest plugin](https://playwright.dev/python/docs/test-runners) · [Trace Viewer](https://playwright.dev/python/docs/trace-viewer)
- Releases: [Playwright release notes](https://playwright.dev/python/docs/release-notes) · [playwright-python](https://github.com/microsoft/playwright-python/releases)
- Companion skills: [python-stack](../python-stack/references/foundation/GUIDE.md), [chrome-devtools](../chrome-devtools/SKILL.md) (accessibility, Lighthouse, and performance audits), [performance](../python-stack/references/performance.md) (load, not browser, testing).
