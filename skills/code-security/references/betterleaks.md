---
name: betterleaks
description: "Scan the working tree and history for secrets; handle confirmed exposure."
---

# Betterleaks

Find credentials before they reach a remote and the ones that already did; each scope answers a different question, and [code-review](code-review/GUIDE.md) orders the pass.

## Commands

```bash
betterleaks dir . --unsafe-auto-load-config --redact=100 --verbose --no-banner   # check:leaks: working tree, including untracked files
betterleaks git --unsafe-auto-load-config --redact=100 --verbose --no-banner     # check:leaks:full: complete history, the scheduled audit
betterleaks git --unsafe-auto-load-config --redact=100 --staged --verbose --no-banner # ad hoc: only the change about to be committed
betterleaks git --unsafe-auto-load-config --redact=100 --report-format sarif --report-path betterleaks.sarif
betterleaks stdin --redact < <file> # outgoing text: PR bodies, prompts and diffs for another AI command; fail closed
```

Since 1.10, betterleaks reads a target's `.betterleaks.toml` only with `--config <file>` or `--unsafe-auto-load-config`; without either, allowlists and custom rules are silently ignored. Use `--unsafe-auto-load-config` only on the project's own checkout (pass `--config` when the file must exist), never on untrusted targets. `--no-banner` removes decoration; keep `--verbose --redact=100` so finding locations remain actionable without revealing secret values. Full scans retain their scope; never pass `--validation` in hooks or CI so candidate secrets never leave the machine.

These commands target Betterleaks 1.x (locked at 1.10.0). The 2.0 release candidates are out (rc.7 on 2026-11-04) and the migration waits for 2.0.0 final: then change every flag together in this guide, the [Python](../../python-stack/references/foundation/templates/mise.toml) and [OpenTofu](../../infra-as-code/templates/mise.toml) starter tasks, and [scanners](skill-security-review/references/scanners.md), and re-check the code-review Gate and the repository's `check:leaks` tasks.

## Mise Task

Expose two scopes per [mise](../../mise/SKILL.md): copy `check:leaks` and `check:leaks:full` from the Python or OpenTofu starter linked above. The gate scans the working tree, including staged, untracked, and gitignored files such as a local `.env` (allowlist those paths in `.betterleaks.toml` when they legitimately hold values), so the [lefthook](../../github-actions/references/lefthook.md) pre-commit `check:local` run scans every commit before it exists; the scheduled job audits the full history.

## When a Secret Is Found

1. **Contain confirmed exposure**: treat an exposed credential as compromised even after the commit disappears. Prepare rotation and execute it only within the established credential and service authority; a scanning request alone does not authorize rotation. Move the value out of the source per [code-review](code-review/GUIDE.md), and rewrite history only when asked.
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
