---
name: opengrep
description: "Run local intrafile and cross-file taint SAST scans with opengrep."
---

# Opengrep

Run local semantic and taint SAST with `opengrep` (standalone LGPL-2.1 binary, zero Python or server dependency); [code-review](code-review/GUIDE.md) orders the full audit. Prefer `opengrep` for dataflow security bugs (SQLi, SSRF, path traversal, command injection) and `ast-grep` for lightweight syntax/structural repo invariants.

## Commands

```bash
# Local or vendored rules with intrafile + cross-file taint and dataflow traces
opengrep scan --config <rules-dir-or-file> --taint-intrafile --enable-interfile --dataflow-traces --error --strict .

# Severity-filtered JSON or SARIF output for triage and CI code scanning
opengrep scan --config <rules-dir-or-file> --taint-intrafile --severity ERROR --severity WARNING --json-output=.cache/opengrep.json --error .
opengrep scan --config <rules-dir-or-file> --taint-intrafile --sarif-output=.cache/opengrep.sarif --error .

# Diff-scoped scan against a base ref (clean working tree required)
opengrep scan --config <rules-dir-or-file> --baseline-commit=origin/main --taint-intrafile --error .

# Ad-hoc semantic hunt and local rule verification
opengrep scan --lang python --pattern '<pattern>' --quiet .
opengrep test <rules-dir> && opengrep validate <rules-dir>
```

Keep rules offline in `.opengrep/rules/` or a commit-SHA-pinned local checkout of `opengrep-rules` (targeting language subdirs such as `python/`); if pulling an upstream third-party rule repo via `--config git+<url>#<ref>`, note that branches/tags are mutable and scope `--skip-invalid-configs` only to upstream bundles with non-rule YAML (never on local `.opengrep/rules/` `--strict` gates).

## Project CI / Mise Task (Opt-In)

Pin `opengrep` in the repository's `mise.toml` (and regenerate `mise.lock`) before wiring `check:sast`—never rely on global workstation tools in CI (on `v2.0.0`, use `"github:opengrep/opengrep"` with `bin = "opengrep"` and explicit per-platform `asset_pattern` entries for `opengrep_linux_aarch64`, `opengrep_linux_x86`, and `opengrep_osx_arm64` until the `aqua` registry updates). Bound cross-file CI runs with `--interfile-depth=3`, `--interfile-timeout=30`, `--max-memory=<MiB>`, and `--timeout=5`.

## Gotchas

- **Never run `--config auto` on private or client repos**: it sends the project URL to the Semgrep Registry to select rules.
- **Pass `--error` on gates**: `opengrep scan` exits `0` on findings by default; `--strict` also fails on rule/config warnings.
- **Audit inline suppressions**: `nosem`, `nosemgrep`, and `noopengrep` silence findings by default—add `--disable-nosem` during security reviews to inspect suppressed hits.
- **`--baseline-commit` requires a clean tree**: it aborts if unstaged changes exist or the commit/ref is missing.
- **Verify rule licenses before redistributing**: the `opengrep` engine is LGPL-2.1, while third-party rulesets may carry separate rule-license terms.

## Documentation

- [Opengrep](https://opengrep.dev) · [opengrep](https://github.com/opengrep/opengrep) · [opengrep-rules](https://github.com/opengrep/opengrep-rules) · [releases](https://github.com/opengrep/opengrep/releases)
- Companion guides: [code-review](code-review/GUIDE.md), [betterleaks](betterleaks.md), [trivy](trivy/GUIDE.md), [sonarqube](sonarqube.md).
