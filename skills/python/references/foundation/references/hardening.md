# Python Hardening, Workspaces, & Structural Gates

Opt-in supply-chain hardening, workspace/registry layout, and mechanical architecture gates layered onto [foundation](../GUIDE.md).

## Supply-Chain Hardening & `uv audit`

- **Wheel-only builds (`no-build`)**: on wheel-only projects set `[tool.uv] no-build = true` to block sdist build-backend execution. Use `no-binary-package = ["<pkg>"]` sparingly as an exception only for sdist-only packages — `no-binary-package` forces sdist builds on _all_ platforms (even where wheels exist).
- **Release cooldown (`exclude-newer`)**: on team/production repos outside personal `0d` defaults, set `[tool.uv] exclude-newer = "3d"` (`exclude-newer-package = { "<pkg>" = false }` or an ISO date override) to buffer fresh releases ahead of malware reports. Combine with the malware-check rule for `uv add`/`uv sync` in [uv](../GUIDE.md#uv).
- **Inspect, export, & audit**: inspect `.venv/` via `uv pip show`; unset `UV_*` (`UV_PROJECT`) on sibling repos instead of `--no-config`; see [PyPI publishing](pypi.md) for hashed `uv export` wheel checks. Triage `uv audit` by upgrading first (`uv lock --upgrade-package <pkg>`) or recording `[tool.uv.audit] ignore-until-fixed = ["GHSA-..."]` (a list of string advisory IDs with dated TOML comments — never CLI `--ignore`).

## Workspaces & Internal Registries

- **Shared root lockfile**: share one root `uv.lock` across `[tool.uv.workspace]` members (`workspace = true` in `[tool.uv.sources]`, target individual packages with `--package <member>`, and run `deptry` and `ty` per member).
- **Private registries**: declare internal indexes via `[[tool.uv.index]]` with `keyring-provider = "subprocess"`; never place credentials or tokens in `pyproject.toml`.

## Architecture & Structural Gates (Opt-In)

Prefer mechanical rules over `AGENTS.md` prose once layers or recurring invariants grow:

- **Module boundaries (`tach` or `import-linter`)**:
  - **`tach` (fast Rust core, explicit interfaces, live graph)**: add `--dev tach` (malware-checked `uv add`), initialize `tach.toml` (`tach init` / `tach sync`), wire `uv run --locked tach check --exact` as `check:arch` in `check:local` (use `--output json` for agent parsing), and inspect real imports offline via `uv run --locked tach show --mermaid -o -` (never `--web`, which uploads to a remote viewer).
  - **`import-linter` (layered/forbidden contracts)**: add `--dev import-linter`, configure `[tool.importlinter]` (`root_package`) + `[[tool.importlinter.contracts]]` (`layers`/`forbidden`/`acyclic_siblings`), and wire `uv run --locked lint-imports --no-logo` into `check:local` when layered contracts fit better than per-module allowlists.
- **Custom AST invariants (`ast-grep`)**: pin `ast-grep` in `mise.toml` (re-lock), add `sgconfig.yml` (`ruleDirs: [.ast-grep/rules]`, `testDirs: [.ast-grep/tests]`) with `severity: error` rules and remediation `message:`, wire `ast-grep scan` into `check:local`, run `ast-grep test`, and keep `--custom-languages` at `ignore`.

Sources: [uv settings](https://docs.astral.sh/uv/reference/settings/) · [uv workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/) · [tach](https://docs.gauge.sh/) · [import-linter](https://import-linter.readthedocs.io/) · [ast-grep](https://ast-grep.github.io/).
