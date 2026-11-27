# BDD & Stakeholder Acceptance Reports (Opt-In)

Add `pytest-bdd` + Allure 3 only when non-technical stakeholders review acceptance criteria or need progress reports—keep minimal starters free of BDD deps.

## Intake & Gherkin v6

- **Lifecycle**: plan in [openspec](../../../../openspec/SKILL.md) `openspec/changes/<id>/` (or standalone PRDs, audited via `fmind-review-spec`) → Example Mapping (`Feature` + non-goals → `Rule:` → `Scenario`/`Examples:` → questions as `@wip`) into `features/<cap>.feature` → implement & un-`@wip` → verify (`fmind-review-test`, `fmind-review-completeness`) → `openspec archive` + publish (`mise run report:bdd`). Match capability slugs (`openspec/specs/<cap>/spec.md` ↔ `features/<cap>.feature`) and link rather than duplicating `Examples:` tables in OpenSpec.
- **Root specs & ownership**: set `bdd_features_base_dir = "features"` in `[tool.pytest]`; add `features/README.md` (allowed `@tags`, `@wip` flow) and pair `/features/`, `/tests/bdd/`, and `/openspec/specs/` in `.github/CODEOWNERS`.
- **Gherkin v6**: group under `Rule:` (Allure `story`) with `1`–`3` `Background:` steps; write `3`–`5` declarative BRIEF steps, one `When`, third-person actors, and `But` for negatives (business outcomes + `@sla` only). Use `datatable`/`docstring`, `parsers.parse`, and `@wip` on future `Examples:`; register markers (`wip`, `sla`, `smoke`, `e2e`, `integration`) under `strict = true` + `filterwarnings = ["error"]`.
- **Hygiene**: scaffold steps with `uv run --locked pytest --generate-missing tests/bdd`; for `check:bdd`, add `reformat-gherkin` (`dev`, [uv](../../foundation/GUIDE.md#uv)) and gate with `reformat-gherkin --check features` + `pytest --collect-only -q tests/bdd`.

## Binding, Hooks & Plugins

- **Binding & install**: bind specs in `tests/bdd/test_features.py` via `scenarios(".")`. Keep thin steps in `tests/bdd/conftest.py` (or `test_<feature>.py`); split modules via top-level `tests/conftest.py` `pytest_plugins = [...]` (plain `import` hides fixtures, nested `conftest.py` forbids `pytest_plugins`, `import *` fails `F403`). Install `uv add --dev 'pytest-bdd>=9.0' 'allure-pytest-bdd>=2.16.2'`—never alongside `allure-pytest`. Attach `@sla` JSON via `allure.attach(..., attachment_type=allure.attachment_type.JSON)`.
- **Hooks ([bdd-conftest.py](../templates/bdd-conftest.py))**: copy to `tests/bdd/conftest.py` for `@issue_*`/`@severity_*` under `strict = true`, `Feature → Rule → Scenario` nesting, and `@wip` skips (`request.node.get_closest_marker("wip")`; `scenario.tags` omits inherited tags).

## Quality Gates, Reports & Agent Usage

- **PR gate vs Allure Quality Gates**: keep `mise run test` on `-m "not integration and not e2e and not wip"` (`--force-enable-socket` in `report:bdd` only for `@e2e`/`@integration`). Copy [allurerc.yaml](../templates/allurerc.yaml) and pin `"npm:allure" = "<version>"` in `mise.toml`.
- **Compile, history, & governance**: compile via `allure generate` (not `allure awesome`) so `qualityGate.rules` run and non-`@wip` failures exit `1`; add `@guardrail` and `@wip` budget rules as needed. For trend history on `main`, set `historyPath: .cache/history.jsonl` in `allurerc.yaml` or run `allure history --history-path <file>.jsonl` (`allure generate` rejects `--history-path`).
- **Sanitize & deliver**: copy [report_bdd.py](../templates/report_bdd.py) to `tests/bdd/report_bdd.py` (`--allure-no-capture` omits stdout/stderr). Upload `.cache/allure-report/index.html` (or mount under `site/bdd/index.html` after `zensical build --clean --strict` per [mounted portals](../../../../docs/references/site/references/configuration.md#mounted-portals); never publish private test data publicly), summarize in `$GITHUB_STEP_SUMMARY`, and attach checks via `allure check --name "<check>" -- <cmd>`.
- **AI agents (`allure agent`)**: run `allure agent inspect --output .cache/allure-agent --report off .cache/allure-results` and query JSON via `allure agent query --from .cache/allure-agent summary|findings|tests` (pass `--expect-label tag=sla --expect-attachments 1` on `-m sla`; rerun failures via `allure agent --rerun-latest --rerun-preset failed -- <cmd>`).

### Holdout Scenarios

- **Split public contract from hidden holdouts**: keep stakeholder specs in `features/` (guarded by `CODEOWNERS` and test-weakening diffs). On high-autonomy runs, store black-box holdouts outside the agent workspace (private repo or CI-only checkout), run in an isolated evaluator, and feed back only sanitized `allure agent query` findings.

```toml
# mise.toml (opt-in; pairs with allurerc.yaml and tests/bdd/report_bdd.py)
[tools]
"npm:allure" = "<version>"

[tasks."report:bdd"]
description = "Run BDD specs (including @wip), sanitize results, and enforce Allure 3 Quality Gates"
run = "uv run --locked python tests/bdd/report_bdd.py"
```

Sources: [pytest-bdd](https://pytest-bdd.readthedocs.io/en/latest/) · [Allure pytest-bdd](https://allurereport.org/docs/pytestbdd/) · [Allure 3](https://allurereport.org/docs/v3/) · [Gherkin Reference](https://cucumber.io/docs/gherkin/reference/) · [reformat-gherkin](https://github.com/ducminh-phan/reformat-gherkin).
