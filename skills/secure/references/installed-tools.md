# Installed Tool Auditing

Audit the exact dependency graphs already installed by mise. Start from `mise ls --json --installed`, audit every installed version and retain its install path and top-level version, and inspect only declared `npm:` and `pipx:` environments.

- For npm tools, copy mise's installed dependency lock into owner-only temporary storage and run `pnpm audit --lockfile-only --json` against that copy. Never generate a new graph and call it installed evidence.
- For pipx tools, run `pip-audit --path` against the environment's actual `site-packages`; never pass `--fix`.
- Report the tool, installed version, vulnerable package/version, dependency chain, advisory, and available fixed versions.
- Treat a missing lock, opaque bundle, skipped dependency, malformed response, or advisory-service failure as a coverage gap. Do not report an all-clear when any gap remains.

Only package names and versions needed for the advisory query may leave the machine. Never include registry credentials, environment variables, package source, or configuration contents in a report.
