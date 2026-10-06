# Installed Tool Auditing

Audit the exact npm and pipx dependency graphs already installed by mise. Start with `mise ls --json --installed`, retain every declared `npm:` and `pipx:` tool's install path and top-level version, and inspect each environment in place.

- **Scan npm tools with Trivy**: run `trivy --config <reviewed-policy.yaml> fs --scanners vuln --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL --ignore-unfixed=false --file-patterns 'pnpm:aube-lock\.yaml'` on the install directory (match pip-audit's all-severity report) (Trivy skips the aube name otherwise); confirm the report contains a `pnpm` target, and never resolve a replacement graph.
- **Audit pipx tools with pip-audit**: locate the environment's actual `site-packages` directory and run `uvx pip-audit --path <site-packages>` without `--fix`.
- **Report each vulnerable path**: the tool, installed version, vulnerable package and version, dependency chain, advisory, and available fixed versions.
- **No all-clear with coverage gaps**: treat a missing lock or environment, skipped dependency, malformed scanner response, or advisory-service failure as a coverage gap. Do not report an all-clear while a gap remains.

Only package names and versions required for the advisory query may leave the machine. Exclude registry credentials, environment variables, source files, and configuration contents from reports.
