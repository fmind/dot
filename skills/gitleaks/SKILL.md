---
name: gitleaks
description: Detect leaked secrets with gitleaks in staged changes, the working tree, or full git history; handle allowlists and rotation. Use for any gitleaks scan or leaked credential.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/gitleaks
  created: "2026-09-02"
  updated: "2026-09-10"
---

# Gitleaks

Find credentials before they reach a remote and the ones that already did; each scope answers a different question, and [secure](../secure/SKILL.md) orders the pass.

## Commands

```bash
gitleaks git --redact=100 --staged --verbose                        # pre-commit: the change about to be committed
gitleaks git --redact=100 --log-opts="--max-count=100" --verbose    # check:leaks:history: recent commits (bounded, fast)
gitleaks git --redact=100 --verbose                                 # full history: the scheduled audit
gitleaks dir . --redact=100 --verbose                               # working tree, including untracked files
gitleaks git --redact=100 --report-format sarif --report-path gitleaks.sarif
```

## Mise Task

Expose explicit scopes per [mise](../mise/SKILL.md). The normal gate scans working-tree files and bounded history; the [lefthook](../lefthook/SKILL.md) pre-commit scan calls `check:leaks:staged`. Native Git options handle an unborn `HEAD` without a shell wrapper.

```toml
[tasks."check:leaks"]
description = "Scan the working tree and recent commits for leaked secrets"
depends = ["check:leaks:tree", "check:leaks:history"]

[tasks."check:leaks:tree"]
description = "Scan working-tree files, including untracked files"
run = "gitleaks dir . --redact=100 --verbose"

[tasks."check:leaks:history"]
description = "Scan the latest 100 commits reachable from HEAD"
# An unborn HEAD has no history; check:leaks:tree still scans its files.
run = 'gitleaks git --redact=100 --log-opts="--max-count=100 --ignore-missing HEAD --" --verbose'

[tasks."check:leaks:staged"]
description = "Scan only staged changes before committing"
run = "gitleaks git --redact=100 --staged --verbose"
```

## When a Secret Is Found

1. **Rotate first**: a secret in history is compromised even after the commit disappears.
1. **Remove it from the source**: move the value to an environment variable or an encrypted file per [sops-secrets](../sops-secrets/SKILL.md).
1. **Rewrite history only when asked**: rewrites affect every clone; confirm with the user before `git filter-repo`.
1. **Allowlist true false positives** with an inline `gitleaks:allow` comment or a rule in `.gitleaks.toml`, each with a reason.

## Gotchas

- **Shallow CI checkouts**: fetch the depth the task scans (`fetch-depth: 100`) and keep the full-history audit in the scheduled `security.yml` job at `fetch-depth: 0` per [github-actions](../github-actions/SKILL.md).
- **Fresh repository**: `--ignore-missing HEAD --` permits an unborn `HEAD`; the separate working-tree scan remains mandatory. After the first commit, the history scan covers the latest 100 commits reachable from `HEAD`. Choose a named scope instead of changing modes through forwarded flags.
- **`--redact` in shared logs**: never print a found secret in CI output or an uploaded report.

## Documentation

- [gitleaks](https://github.com/gitleaks/gitleaks)
- Companion skills: [secure](../secure/SKILL.md), [lefthook](../lefthook/SKILL.md), [trivy](../trivy/SKILL.md) (also reports secrets in `fs` scans).
