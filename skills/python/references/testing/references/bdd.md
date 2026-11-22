# BDD & Stakeholder Acceptance Reports (Opt-In)

Add `pytest-bdd` + Allure 3 only when non-technical stakeholders (PMs, leaders, clients) co-own acceptance criteria or need readable progress reports—keep minimal Python starters free of BDD deps.

- **Stakeholder specs**: write English Gherkin v6 specs in `tests/features/*.feature` with `3`–`5` coarse business-level steps per scenario (never UI click/selector micro-steps). Cover business behavior and user-visible `@sla` budgets only—keep LOC, lint, and coverage gates in normal unit/lint suites. Protect `/tests/features/` in `.github/CODEOWNERS` only where stakeholders review GitHub PRs.
- **Install & plugin conflict**: `uv add --dev 'pytest-bdd>=9.0' 'allure-pytest-bdd>=2.16.2'`. Never install `allure-pytest` alongside `allure-pytest-bdd` (both register `--alluredir` and crash pytest startup with `ValueError`); `allure-pytest-bdd` alone omits plain unit tests from `allure-results` without `-p no:...`.
- **Binding, markers & `@sla` attachments**: bind specs in `tests/test_*_bdd.py` via `scenarios("features/<name>.feature")`, register every Gherkin `@tag` (`wip`, `sla`, etc.) in `[tool.pytest] markers` under `strict = true` and `filterwarnings = ["error"]`, and attach `@sla` metrics via `allure.attach(json.dumps(metrics, indent=2), name="<sla>.json", attachment_type=allure.attachment_type.JSON)`.
- **CI gate vs. vanilla Allure 3 report**: keep blocking PR CI (`mise run test`) on `-m "not wip"` so unit tests and implemented specs pass 100%. Pin `"npm:allure" = "<version>"` in `mise.toml` (Node-only, zero Java, zero `package.json`/`node_modules/`). Run `allure awesome .cache/allure-results --single-file --output .cache/allure-report` for a standalone offline HTML report (`allure log` for CLI output; `--history-path <file>.jsonl` / `allure history` for trends).
- **Known caveats**: `allure-pytest-bdd` writes `{"name": "host", "value": "<hostname>"}` into `*-result.json` and Allure 3 `--hide-labels host` still embeds it in base64 `window.allureReportData`—generate externally shared reports in ephemeral CI (or strip `host` labels before compiling). `pytest-bdd 9` executes `Rule:` blocks, while `allure-pytest-bdd 2.16.x` flattens scenarios under `Feature:`; use tags or `@allure.story(...)` if sub-grouping matters.

```toml
# mise.toml (opt-in)
[tools]
"npm:allure" = "<version>"

[tasks."report:bdd"]
description = "Run BDD specs (including @wip) and generate vanilla single-file Allure 3 HTML"
run = """
set -eu
rm -rf .cache/allure-results .cache/allure-report
mkdir -p .cache
rc=0
uv run --locked pytest -q --tb=line tests/test_*_bdd.py --alluredir=.cache/allure-results || rc=$?
[ "$rc" -le 1 ] || exit "$rc"
allure awesome .cache/allure-results --single-file --output .cache/allure-report
allure log .cache/allure-results
"""
```

Sources: [pytest-bdd](https://pytest-bdd.readthedocs.io/en/latest/) · [Allure pytest-bdd](https://allurereport.org/docs/pytestbdd/) · [Allure 3](https://allurereport.org/docs/v3/) · [Gherkin Reference](https://cucumber.io/docs/gherkin/reference/).
