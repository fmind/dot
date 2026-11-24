# BDD & Stakeholder Acceptance Reports (Opt-In)

Add `pytest-bdd` + Allure 3 only when non-technical stakeholders review acceptance criteria or need progress reports—keep minimal starters free of BDD deps.

## Intake & Gherkin v6

- **Lifecycle**: audit PRDs (`fmind-review-spec`) → Example Mapping (`Feature` + non-goals → `Rule:` invariants → `Scenario`/`Examples:` happy/boundary/failure → questions as `@wip`/`Decisions`) into `features/*.feature` → verify (`fmind-review-test` + `fmind-review-completeness`) → publish (`mise run report:bdd`).
- **Root specs & ownership**: set `bdd_features_base_dir = "features"` in `[tool.pytest]`; add `features/README.md` (allowed `@tags`, `@wip` flow) for GitHub edits and pair `/features/` + `/tests/bdd/` in `.github/CODEOWNERS`.
- **Gherkin v6**: group under `Rule:` (Allure `story`) with `1`–`3` `Background:` steps; write `3`–`5` declarative BRIEF steps, one `When`, third-person actors, and `But` for negatives (business behavior + `@sla` only; no UI micro-steps). Use `datatable`/`docstring`, `parsers.parse`, and `@wip` on future `Examples:`; register markers (`wip`, `sla`, `smoke`, `e2e`, `integration`) under `strict = true` + `filterwarnings = ["error"]`, and map `@issue_<id>`/`@severity_<level>` via `pytest_bdd_apply_tag`.
- **Hygiene**: scaffold steps with `uv run --locked pytest --generate-missing tests/bdd`; for `check:bdd`, add `reformat-gherkin` to `dev` (`UV_MALWARE_CHECK=1 uv add --preview-features malware-check --dev reformat-gherkin`) and gate via `uv run --locked reformat-gherkin --check features` + `uv run --locked pytest --collect-only -q tests/bdd`.

## Binding, Hooks & Plugins

- **Binding & install**: bind all specs in `tests/bdd/test_features.py` via `scenarios(".")`. Define thin step adapters in `tests/bdd/conftest.py` (or `tests/bdd/test_<feature>.py`); to split step modules, list them in `pytest_plugins = [...]` in top-level `tests/conftest.py` (plain `import` hides step fixtures, nested `conftest.py` forbids `pytest_plugins`, and `import *` fails Ruff `F403`). Install `uv add --dev 'pytest-bdd>=9.0' 'allure-pytest-bdd>=2.16.2'`—never alongside `allure-pytest` (duplicate `--alluredir` crashes with `ValueError`). Attach `@sla` JSON via `allure.attach(json.dumps(metrics, indent=2), name="<sla>.json", attachment_type=allure.attachment_type.JSON)`.
- **Hooks ([bdd-conftest.py](../templates/bdd-conftest.py))**: copy to `tests/bdd/conftest.py` to map `@issue_*`/`@severity_*` under `strict = true`, set `allure.dynamic.story(scenario.rule.name)` for `Feature → Rule → Scenario` nesting, and skip missing steps via `request.node.get_closest_marker("wip")` (`scenario.tags` omits inherited tags).

## Quality Gates, Reports & Agent Usage

- **PR gate vs Allure Quality Gates**: keep `mise run test` on `-m "not integration and not e2e and not wip"` (`--force-enable-socket` in `report:bdd` only for `@e2e`/`@integration`). Copy [allurerc.yaml](../templates/allurerc.yaml) (YAML + CEL, zero JS) and pin `"npm:allure" = "<version>"` in `mise.toml`.
- **Compile & enforce governance gates**: compile via `allure generate` (not `allure awesome`) so `qualityGate.rules` run, verdicts embed in Awesome HTML grouped by `["feature", "story"]`, and non-`@wip` failures exit `1`. For stakeholder governance suites, add `@guardrail` must-pass (`maxFailures: 0`, `minTestsCount: 1`) and `@wip` budget cap rules.
- **Sanitize & deliver**: copy [report_bdd.py](../templates/report_bdd.py) to `tests/bdd/report_bdd.py` to strip `host` labels and repo/`$HOME` paths without mutating `*-attachment.json` (`--allure-no-capture` omits stdout/stderr), then fail closed (`assert_no_leaks`) on residual tokens, paths, or diff hunks before HTML generation. Upload `.cache/allure-report/index.html` (`--history-path <file>.jsonl` on `main`), summarize in `$GITHUB_STEP_SUMMARY`, and attach extra checks via `allure check --name "<check>" -- <cmd>`.
- **AI agents (`allure agent`)**: run `allure agent inspect --output .cache/allure-agent --report off .cache/allure-results` and query JSON via `allure agent query --from .cache/allure-agent summary|findings|tests` for `fmind-review-test`/`fmind-review-completeness`. Pass `--expect-label tag=sla --expect-attachments 1` to `allure agent inspect` on `-m sla` runs; rerun failures via `allure agent --rerun-latest --rerun-preset failed -- <cmd>`.

### Holdout Scenarios

- **Split public contract from hidden holdouts**: keep stakeholder-reviewed contract specs in repo `features/` (guarded by `CODEOWNERS` and the test-weakening diff check). On high-autonomy agent runs, store extra black-box holdout `.feature` files and step bindings outside the coding agent's workspace (separate private repo or CI-only checkout), run them in an isolated evaluator step against the built artifact or service, and return only sanitized `allure agent query` findings to prevent overfitting.

```toml
# mise.toml (opt-in; pairs with allurerc.yaml and tests/bdd/report_bdd.py)
[tools]
"npm:allure" = "<version>"

[tasks."report:bdd"]
description = "Run BDD specs (including @wip), sanitize results, and enforce Allure 3 Quality Gates"
run = "uv run --locked python tests/bdd/report_bdd.py"
```

Sources: [pytest-bdd](https://pytest-bdd.readthedocs.io/en/latest/) · [Allure pytest-bdd](https://allurereport.org/docs/pytestbdd/) · [Allure 3](https://allurereport.org/docs/v3/) · [Gherkin Reference](https://cucumber.io/docs/gherkin/reference/) · [reformat-gherkin](https://github.com/ducminh-phan/reformat-gherkin).
