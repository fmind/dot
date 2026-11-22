# BDD & Stakeholder Acceptance Reports (Opt-In)

Add `pytest-bdd` + Allure 3 only when non-technical stakeholders (PMs, leaders, clients) review acceptance criteria or need readable progress reports—keep minimal Python starters free of BDD deps.

- **Four-stage lifecycle**: audit upstream manager specs/PRDs with `fmind-review-spec` → distill executable Gherkin specs in `features/*.feature` → verify step strength, anti-weakening, and traceability with `fmind-review-test` + `fmind-review-completeness` → publish stakeholder reports via `mise run report:bdd`.
- **Stakeholder-friendly specs (`features/`)**: set `bdd_features_base_dir = "features"` in `[tool.pytest]` so specs live at repo root instead of inside `tests/`. Put user-story context (`As a ... I want ... So that ...`) in `Feature:`, write `3`–`5` coarse business steps per scenario (never UI micro-steps), and cover business behavior and `@sla` budgets only (keep lint and coverage in unit/lint suites).
- **Parameterized thresholds & `@tags` guide**: use `parsers.parse` for thresholds and `Scenario Outline` + `Examples:` tables so owners can tune cases without breaking step phrasing; add a short `features/README.md` listing allowed `@tags` when stakeholders edit specs in GitHub.
- **Zero-orphan binding & ownership**: bind the folder from one `tests/bdd/test_features.py` via `scenarios(".")` (importing shared step modules in `tests/bdd/conftest.py`) so new `.feature` files always run. Keep steps thin adapters over domain helpers, and protect `/features/` and `/tests/bdd/` together in `.github/CODEOWNERS` where PR review governs spec changes.
- **`@wip` optics**: in `tests/bdd/conftest.py`, convert missing steps on `@wip` scenarios into clean `Skipped` entries in Allure (instead of alarming `Broken` stack traces) while non-`@wip` missing steps still fail loudly:

```python
# tests/bdd/conftest.py
def pytest_bdd_step_func_lookup_error(request, feature, scenario, step, exception):
    if "wip" in scenario.tags:
        pytest.skip(f"WIP step not yet implemented: {step.name}")
```

- **Install, plugin conflict & `@sla` attachments**: `uv add --dev 'pytest-bdd>=9.0' 'allure-pytest-bdd>=2.16.2'`. Never install `allure-pytest` alongside `allure-pytest-bdd` (both register `--alluredir` and crash pytest startup with `ValueError`); `allure-pytest-bdd` alone omits plain unit tests from `allure-results` without `-p no:...`. Register every Gherkin `@tag` (`wip`, `sla`, etc.) in `[tool.pytest] markers` under `strict = true` and `filterwarnings = ["error"]`, and attach `@sla` metrics via `allure.attach(json.dumps(metrics, indent=2), name="<sla>.json", attachment_type=allure.attachment_type.JSON)`.
- **CI gate & sanitized Allure 3 HTML**: extend blocking PR CI (`mise run test`) from `-m "not integration and not e2e"` to `-m "not integration and not e2e and not wip"` so unit tests and implemented specs pass 100% (add `--force-enable-socket` to `report:bdd` only for `@e2e`/`@integration`). Pin `"npm:allure" = "<version>"` in `mise.toml` (Node-only, zero Java) and strip `{"name": "host"}` from `*-result.json` before compiling—Allure 3 `--hide-labels host` still embeds hostnames in base64 `window.allureReportData`.
- **Report delivery**: upload `.cache/allure-report/index.html` as a CI artifact (or GitHub Pages on `main` with `--history-path <file>.jsonl` / `allure history` for trends) and append a concise Markdown status table (or `allure log`) to `$GITHUB_STEP_SUMMARY` for PRs.
- **Known caveat**: `pytest-bdd 9` executes `Rule:` blocks, while `allure-pytest-bdd 2.16.x` flattens scenarios under `Feature:`; use tags or `@allure.story(...)` if sub-grouping matters.

```toml
# mise.toml (opt-in)
[tools]
"npm:allure" = "<version>"

[tasks."report:bdd"]
description = "Run BDD specs (including @wip) and generate sanitized single-file Allure 3 HTML"
run = '''
set -eu
rm -rf .cache/allure-results .cache/allure-report
mkdir -p .cache
rc=0
uv run --locked pytest -q --tb=line tests/bdd --alluredir=.cache/allure-results || rc=$?
[ "$rc" -le 1 ] || exit "$rc"
uv run --locked python -c '
import glob, json, pathlib
for f in glob.glob(".cache/allure-results/*-result.json"):
    p = pathlib.Path(f)
    data = json.loads(p.read_text(encoding="utf-8"))
    data["labels"] = [lbl for lbl in data.get("labels", []) if lbl.get("name") != "host"]
    p.write_text(json.dumps(data), encoding="utf-8")
'
allure awesome .cache/allure-results --single-file --output .cache/allure-report
allure log .cache/allure-results
'''
```

Sources: [pytest-bdd](https://pytest-bdd.readthedocs.io/en/latest/) · [Allure pytest-bdd](https://allurereport.org/docs/pytestbdd/) · [Allure 3](https://allurereport.org/docs/v3/) · [Gherkin Reference](https://cucumber.io/docs/gherkin/reference/).
