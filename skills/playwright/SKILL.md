---
name: playwright
description: Drive browsers with Python Playwright for end-to-end tests, screenshots, traces, and code generation. Use for browser automation or e2e testing.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/playwright
  created: "2026-09-02"
  updated: "2026-09-06"
---

# Playwright

Use Playwright for browser automation and end-to-end tests. Test strategy belongs to [quality-assurance](../quality-assurance/SKILL.md) and interface critique to [product-design-review](../product-design-review/SKILL.md); this skill owns the tool: browsers, commands, and the official skills.

## Workflow

1. **Pin the Python integration**: `uv add --dev playwright pytest-playwright`, then `uv run playwright install chromium`; keep both packages in `uv.lock`. If Linux system libraries are missing, report the administrator-owned prerequisite instead of invoking the privileged `install-deps` command.
1. **Explore and record**: `uv run playwright codegen --target python <url>` records Python actions; `uv run playwright screenshot <url> <file>` and `uv run playwright pdf <url> <file>` produce review evidence.
1. **Write resilient tests**: use the pytest `page` fixture, role or label locators, and web-first `expect` assertions; keep test state isolated and deterministic.
1. **Run tests**: `uv run pytest tests/e2e --browser chromium --tracing retain-on-failure --screenshot only-on-failure`; open a saved trace with `uv run playwright show-trace <trace.zip>`.
1. **Verify**: a green pytest run plus the artifact (screenshot, trace, or report) the task asked for.

## Gotchas

- **Authority**: a test request does not authorize reusing a logged-in browser, synchronizing cookies, entering passwords or MFA, creating accounts, bypassing CAPTCHA, accepting legal terms, making purchases, or paying for cloud browsers or tunnels; stop and ask.
- **Browser cache**: binaries live in `~/.cache/ms-playwright`; `playwright uninstall` frees them.
- **Version skew**: browsers match the Playwright version that installed them; rerun `uv run playwright install chromium` after an upgrade.
- **Headless by default**: pass `--headed` to watch a run; keep CI headless.

## Official Skills

No separate agent-skill install is required for the Python test workflow; keep Playwright behavior pinned through the project's uv lockfile.

## Documentation

- [Playwright for Python](https://playwright.dev/python/docs/intro) · [pytest plugin](https://playwright.dev/python/docs/test-runners) · [Trace Viewer](https://playwright.dev/python/docs/trace-viewer)
- Accessibility and performance evidence: [chrome-devtools](../chrome-devtools/SKILL.md) owns the MCP integration and reviewed package version; `lighthouse <url> --output json` stays the one-shot audit.
- Companion skills: [python-stack](../python-stack/SKILL.md), [quality-assurance](../quality-assurance/SKILL.md), [product-design-review](../product-design-review/SKILL.md), [chrome-devtools](../chrome-devtools/SKILL.md), [benchmark](../benchmark/SKILL.md) (load, not browser, testing).
