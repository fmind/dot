---
name: release
description: "Prepare, publish when requested, or verify versioned releases."
---

# Release

Prepare, publish, or verify versioned releases using Conventional Commits, `git-cliff`, signed tags, and GitHub release attestations; prefer the repository's own release task when present.

## Workflow

1. **Select mode**: preparation, authorized publication, or read-only verification; record repo, candidate SHA, target version, and release owner (CLI vs CI workflow).
1. **Prepare**: verify a clean candidate and absent tag, run the full gate, and follow [publish.md](references/publish.md).
1. **Publish only on request**: use one owner — never run manual `gh release create` against a tag-triggered release workflow.
1. **Verify**: reconcile the peeled tag SHA, exact-commit CI/CD, release state, and asset checksums/attestations per [verify.md](references/verify.md).
1. **Report**: URL, version, SHA, verified artifacts, and any unproven boundary (local gate vs remote release vs deploy).

## Gotchas

- **Published tags are immutable**: never move a published tag or overwrite assets to mask a failed check.
- **Qualify the exact candidate**: preserve unrelated dirty edits and gate the materialized release commit, not an earlier `HEAD`.
- **Verification is read-only**: auditing a release grants zero authority to retag or re-upload.
- **Keep `vX.Y.Z` tags and inspect static versions**: retain the `v` prefix and check non-VCS version constants alongside `git-cliff`.

## Documentation

- [git-cliff](https://git-cliff.org) · [gh release manual](https://cli.github.com/manual/gh_release) · [GitHub release integrity](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/verify-release-integrity) · [git-cliff releases](https://github.com/orhun/git-cliff/releases) · [changelog](https://github.com/orhun/git-cliff/blob/main/CHANGELOG.md)
- Companion skills: [commit messages](../../SKILL.md#commit-messages), [pull-request](../../../gh/references/pull-request.md), [mise](../../../mise/SKILL.md).
