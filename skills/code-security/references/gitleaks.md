---
name: gitleaks
description: "Secret scanning and verified exposure handling."
---

# Gitleaks

Find credentials before they reach a remote and the ones that already did; each scope answers a different question, and [code-review](code-review/GUIDE.md) orders the pass.

## Commands

```bash
gitleaks dir . --redact=100 --verbose --no-banner                # check:leaks: working tree, including untracked files
gitleaks git --redact=100 --verbose --no-banner                  # check:leaks:full: complete history, the scheduled audit
gitleaks git --redact=100 --staged --verbose --no-banner         # ad hoc: only the change about to be committed
gitleaks git --redact=100 --report-format sarif --report-path gitleaks.sarif
```

`--no-banner` removes decoration; keep `--verbose --redact=100` so finding locations remain actionable without revealing secret values. Full scans retain their scope.

## Mise Task

Expose two scopes per [mise](../../mise/SKILL.md). The gate scans the working tree, including staged, untracked, and gitignored files such as a local `.env` (allowlist those paths in `.gitleaks.toml` when they legitimately hold values), so the [lefthook](../../github-actions/references/lefthook.md) pre-commit `check` run scans every commit before it exists; the scheduled job audits the full history.

```toml
[tasks."check:leaks"]
description = "Scan working-tree files, including untracked files, for leaked secrets"
run = "gitleaks dir . --redact=100 --verbose --no-banner"

[tasks."check:leaks:full"]
description = "Scan the complete Git history (weekly in security.yml; needs a full clone)"
run = "gitleaks git --redact=100 --verbose --no-banner"
```

## When a Secret Is Found

1. **Contain confirmed exposure**: treat an exposed credential as compromised even after the commit disappears. Prepare rotation first and execute it only within the established credential and service authority; a scanning request alone does not authorize rotation.
1. **Remove it from the source**: move the value to an environment variable or an encrypted file per [sops-secrets](../../sops-secrets/SKILL.md).
1. **Rewrite history only when asked**: rewrites affect every clone; confirm with the user before `git filter-repo`.
1. **Allowlist true false positives**: use an inline `gitleaks:allow` comment or a rule in `.gitleaks.toml`, each with a reason.

## Gotchas

- **Policy is part of the evidence**: inspect effective configuration, ignore files, baselines, and inline `gitleaks:allow` comments. For an untrusted candidate, run from a trusted directory with reviewed `--config` and `--gitleaks-ignore-path` files and `--ignore-gitleaks-allow`; do not let the candidate suppress its own findings. Redaction protects output, not scan completeness.
- **Fetch full history for audits**: the scheduled `security.yml` job needs `fetch-depth: 0` per [github-actions](../../github-actions/references/ci-cd/GUIDE.md); a shallow clone silently narrows `check:leaks:full`.
- **Rescan after bypassed hooks**: a commit made with `--no-verify` or outside the hooks is caught only by the weekly full-history audit; run `check:leaks:full` after importing foreign history.
- **Always `--redact` shared logs**: never print a found secret in CI output or an uploaded report.

## Documentation

- [gitleaks](https://github.com/gitleaks/gitleaks)
- Releases: [gitleaks](https://github.com/gitleaks/gitleaks/releases)
- Companion skills: [code-review](code-review/GUIDE.md), [lefthook](../../github-actions/references/lefthook.md), [trivy](trivy/GUIDE.md) (its `secret` scanner stays disabled; keep one secret scanner per repository).
