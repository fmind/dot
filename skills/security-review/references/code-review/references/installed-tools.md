# Installed Tool Auditing

Audit the exact npm and pipx dependency graphs already installed by mise. Start with `mise ls --json --installed`, retain every declared `npm:` and `pipx:` tool's install path and top-level version, and inspect each environment in place.

- For npm tools, copy mise's installed `aube-lock.yaml` into owner-only temporary storage and run `trivy fs --scanners vuln` against the copy; never resolve a replacement graph.
- For pipx tools, locate the environment's actual `site-packages` directory and run `pip-audit --path <site-packages>` without `--fix`.
- Report the tool, installed version, vulnerable package and version, dependency chain, advisory, and available fixed versions.
- Treat a missing lock or environment, skipped dependency, malformed scanner response, or advisory-service failure as a coverage gap. Do not report an all-clear while a gap remains.

Only package names and versions required for the advisory query may leave the machine. Exclude registry credentials, environment variables, source files, and configuration contents from reports.
