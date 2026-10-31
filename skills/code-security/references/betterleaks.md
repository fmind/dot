---
name: betterleaks
description: "Scan the working tree and history for secrets; handle confirmed exposure."
---

# Betterleaks

Find credentials before they reach a remote and the ones that already did; each scope answers a different question, and [code-review](code-review/GUIDE.md) orders the pass.

## Commands

```bash
betterleaks dir . --redact=100 --verbose --no-banner                # check:leaks: working tree, including untracked files
betterleaks git --redact=100 --verbose --no-banner                  # check:leaks:full: complete history, the scheduled audit
betterleaks git --redact=100 --staged --verbose --no-banner         # ad hoc: only the change about to be committed
betterleaks git --redact=100 --report-format sarif --report-path betterleaks.sarif
```

`--no-banner` removes decoration; keep `--verbose --redact=100` so finding locations remain actionable without revealing secret values. Full scans retain their scope; never pass `--validation` in hooks or CI so candidate secrets never leave the machine.

## Mise Task

Expose two scopes per [mise](../../mise/SKILL.md). The gate scans the working tree, including staged, untracked, and gitignored files such as a local `.env` (allowlist those paths in `.betterleaks.toml` when they legitimately hold values), so the [lefthook](../../github-actions/references/lefthook.md) pre-commit `check` run scans every commit before it exists; the scheduled job audits the full history.

```toml
[tasks."check:leaks"]
description = "Scan working-tree files, including untracked files, for leaked secrets"
run = "betterleaks dir . --redact=100 --verbose --no-banner"

[tasks."check:leaks:full"]
description = "Scan the complete Git history (weekly in security.yml; needs a full clone)"
run = "betterleaks git --redact=100 --verbose --no-banner"
```

## When a Secret Is Found

1. **Contain confirmed exposure**: treat an exposed credential as compromised even after the commit disappears. Prepare rotation first and execute it only within the established credential and service authority; a scanning request alone does not authorize rotation.
1. **Remove it from the source**: move the value to an environment variable injected by the project's secret manager or a scoped launcher, or to the encrypted store the project already uses.
1. **Rewrite history only when asked**: rewrites affect every clone; confirm with the user before `git filter-repo`.
1. **Allowlist true false positives**: use an inline `betterleaks:allow` comment, a scoped rule in `.betterleaks.toml`, or a fingerprint in `.betterleaksignore`, each with a reason.

## Gotchas

- **Policy is part of the evidence**: inspect effective configuration, ignore files, baselines, and inline `betterleaks:allow` or `gitleaks:allow` comments. For an untrusted candidate, run from a trusted directory with reviewed `--config` and `--gitleaks-ignore-path` files and `--ignore-gitleaks-allow`; do not let the candidate suppress its own findings. Redaction protects output, not scan completeness.
- **Fetch full history for audits**: the scheduled `security.yml` job needs `fetch-depth: 0` per [github-actions](../../github-actions/references/ci-cd/GUIDE.md); a shallow clone silently narrows `check:leaks:full`.
- **Rescan after bypassed hooks**: a commit made with `--no-verify` or outside the hooks is caught only by the weekly full-history audit; run `check:leaks:full` after importing foreign history.
- **Always `--redact` shared logs**: never print a found secret in CI output or an uploaded report.

## Documentation

- [betterleaks](https://github.com/betterleaks/betterleaks)
- Releases: [betterleaks](https://github.com/betterleaks/betterleaks/releases)
- Companion skills: [code-review](code-review/GUIDE.md), [lefthook](../../github-actions/references/lefthook.md), [trivy](trivy/GUIDE.md) (its `secret` scanner stays disabled; keep one secret scanner per repository).
