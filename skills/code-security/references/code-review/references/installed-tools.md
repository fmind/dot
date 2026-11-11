# Installed Tool Auditing

Audit the exact `npm:` and `pypi:` graphs installed by mise: filter `mise ls --json --installed` to `active` entries (skipping aliases and stale versions) and inspect each install path in place without resolving replacement graphs.

- **npm tools (Trivy)**: run `trivy --config <reviewed-policy.yaml> fs --scanners vuln --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL --ignore-unfixed=false --file-patterns 'pnpm:aube-lock\.yaml'` on the install directory (otherwise Trivy skips `aube-lock.yaml`) and confirm a `pnpm` target appears.
- **pypi tools (pip-audit)**: run `uvx pip-audit --path <site-packages>` (without `--fix`) against `<install>/.mise-uv/.venv/lib/python3.*/site-packages`.
- **Report & fail closed**: list tool, version, vulnerable package, chain, advisory, and fixed versions; treat missing locks/envs, skipped packages, or advisory errors as coverage gaps (no all-clear), sending only package names/versions externally.
