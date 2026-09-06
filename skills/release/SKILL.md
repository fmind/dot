---
name: release
description: "Cut or verify a versioned release: bump semver, generate the changelog with git-cliff, tag, and publish on GitHub. Use when releasing or reconciling a published tag."
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/release
  created: "2026-07-04"
  updated: "2026-09-05"
---

# Release

Prepare or verify a versioned release with Conventional Commits, git-cliff, annotated tags, and GitHub release evidence. Use the repository's release task when it owns this lifecycle.

## Workflow

1. **Resolve the mode**: preparation, authorized publication, or read-only verification. Record repository, candidate `git` commit, intended version, and the system that creates the release.
1. **Prepare**: inspect a clean candidate and absent tag, run the required gate, and follow [publish.md](references/publish.md) for manifest/changelog changes. Read [versioning](references/versioning.md) before overriding git-cliff.
1. **Publish only when requested**: use the authorized commit/tag/push path and one release owner; a tag-triggered workflow must not compete with `gh release create`.
1. **Reconcile**: follow [verify.md](references/verify.md) for the peeled tag commit, exact-commit CI/CD, release state, and delivered version; use [asset checks](references/verify-assets.md) for expected checksums and provenance.
1. **Report**: release URL, version, commit, verified artifacts, and any unresolved proof; keep local qualification, remote publication, and deployment distinct.

## Gotchas

- **Immutable tags**: never move a published tag or silently replace assets to repair failed proof.
- **Dirty work**: preserve unrelated edits and qualify the exact materialized candidate; do not use a clean HEAD worktree as proof of uncommitted changes.
- **Authority persists**: an explicit release request authorizes its stated publication steps; verifying an existing release grants no repair or republishing authority.
- **Semver**: retain the `v` tag prefix and the repository's configured git-cliff behavior; explicit version constants still need inspection.

## Documentation

- [git-cliff](https://git-cliff.org) · [gh release manual](https://cli.github.com/manual/gh_release)
- [GitHub release integrity](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/verify-release-integrity)
- Companion skills: [conventional-commit](../conventional-commit/SKILL.md) (commit grammar), [github-pull-request](../github-pull-request/SKILL.md) (merge first), [mise](../mise/SKILL.md) (the gate).
