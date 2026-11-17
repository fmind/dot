---
name: betterleaks
description: "Scan the working tree and history for secrets; handle confirmed exposure."
---

# Betterleaks

Scan working trees and Git history for secrets; [code-review](code-review/GUIDE.md) orders the full audit.

## Commands

```bash
betterleaks dir . --config .betterleaks.toml --redact=100 --verbose --no-banner   # check:leaks: working tree, including untracked files
betterleaks git --config .betterleaks.toml --redact=100 --verbose --no-banner     # check:leaks:full: complete history, the scheduled audit
betterleaks git --config .betterleaks.toml --redact=100 --staged --verbose --no-banner # ad hoc: only the change about to be committed
betterleaks git --config .betterleaks.toml --redact=100 --report-format sarif --report-path betterleaks.sarif
betterleaks stdin --redact < <file> # outgoing text: PR bodies, prompts and diffs for another AI command; fail closed
```

Since 1.10, `.betterleaks.toml` loads only with explicit `--config .betterleaks.toml` (preferred whenever `.betterleaks.toml` exists) or `--unsafe-auto-load-config` (trusted checkouts lacking `.betterleaks.toml` only, never untrusted targets—it also auto-loads legacy `.gitleaks.toml`). Keep `--verbose --redact=100 --no-banner` and never pass `--validation` in hooks/CI so candidate secrets stay local. Commands target Betterleaks 1.x (locked 1.10.1; 2.0.0-rc.7 shipped 2026-11-04—on 2.0.0 final, migrate flags together across this guide, [Python](../../python-stack/references/foundation/templates/mise.toml) and [OpenTofu](../../infra-as-code/templates/mise.toml) starters, [scanners](skill-security-review/references/scanners.md), and repo `check:leaks` tasks).

## Mise Task

Wire `check:leaks` (with [betterleaks.toml](../templates/betterleaks.toml) as `.betterleaks.toml`; scans working tree including untracked/gitignored `.env` unless allowlisted in `.betterleaks.toml`, run pre-commit via [lefthook](../../github-actions/references/lefthook.md)) and `check:leaks:full` (scheduled history audit) per [mise](../../mise/SKILL.md).

## When a Secret Is Found

1. **Contain exposure**: treat leaked credentials as compromised even if deleted; prepare rotation (execute only with credential/service approval), externalize the secret per [code-review](code-review/GUIDE.md), and rewrite history only on request.
1. **Allowlist false positives**: document the reason via inline `betterleaks:allow`, a narrow `.betterleaks.toml` rule, or `.betterleaksignore`.

## Gotchas

- **Audit suppressions**: inspect `.betterleaks.toml`, ignore files, and `betterleaks:allow` / `gitleaks:allow` comments; scan untrusted code from outside with trusted `--config`, `--gitleaks-ignore-path`, and `--ignore-gitleaks-allow`.
- **Full history needs `fetch-depth: 0`** in `security.yml` ([github-actions](../../github-actions/references/ci-cd/GUIDE.md)) and a fresh `check:leaks:full` after `--no-verify` or foreign history imports.
- **Always `--redact`** CI logs and shared reports.

## Documentation

- [betterleaks](https://github.com/betterleaks/betterleaks) · [releases](https://github.com/betterleaks/betterleaks/releases)
- Companion skills: [code-review](code-review/GUIDE.md), [lefthook](../../github-actions/references/lefthook.md), [trivy](trivy/GUIDE.md) (keep Trivy's `secret` scanner disabled).
