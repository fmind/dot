---
name: dot-release
description: Prepare, recover, and verify fmind/dot releases through the repository task. Use when releasing this project or reconciling an interrupted release.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/dot-release
  created: "2026-07-08"
  updated: "2026-09-09"
---

# Dot Release

Use the checkout's release task as the single owner of preparation and publication. The global [release](../../../skills/release/SKILL.md) skill owns generic versioning and publication verification; this skill owns dot's preconditions and recovery.

## Workflow

1. **Resolve the mode**: preparation, authorized release, or read-only reconciliation. The release command commits, pushes, and refreshes the installed CLI; a review or skill invocation alone does not authorize those actions.
1. **Inspect preconditions**: a clean tree on the configured default branch, `gh` authenticated, and `git`, `git-cliff`, `mise`, and `uv` available. Defaults are `main` and `origin`; inspect the task's `--remote` and `--branch` arguments before assuming them. Preserve unrelated work when a precondition fails.
1. **Run the owner**: use the commands below from the repository. The task uses `uv run --frozen --directory dot python -m dot_tasks.release`, avoiding an installed CLI that may lag source.
1. **Read the result**: a new release requires HEAD equal to the fetched upstream branch. Preparation updates `dot/pyproject.toml`, `CHANGELOG.md`, and `dot/uv.lock`, then runs format, check, test, and build. Only those generated release files may change.
1. **Reconcile publication**: the command commits, pushes the specific release commit, creates or validates its annotated tag, pushes that exact tag object, and verifies remote acceptance. It then runs `mise run --force deploy` to refresh the installed CLI. A retry revalidates an existing prepared release instead of creating another version.
1. **Verify delivery**: the tag triggers [cd.yml](../../../.github/workflows/cd.yml). `mise run release -- --wait` observes the exact head/tag CD and checks public wheel/source assets within `--timeout-seconds` (default 1800); without it, success reports dispatch only. Follow the global release skill's [verification](../../../skills/release/references/verify.md) and [asset checks](../../../skills/release/references/verify-assets.md) for deeper artifact and installed-version proof. Local command success does not prove CD completion.

```bash
mise run release          # interactive preparation and publication
mise run release -- -y     # non-interactive, within an authorized release
```

## Recovery

Inspect `git status --short`, the release commit, local tag, and remote state before retrying. [release.py](../../../dot/dot_tasks/release.py) owns recovery; search `run_release`, `_validate_prepared_release`, and `push_release_tag`. Its failure cases are exercised in [test_release.py](../../../dot/tests/test_release.py).

| Failure boundary                                         | Next action                                                                                                                                                                                                                |
| -------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Before a release commit                                  | The command attempts to restore the version, changelog, and lockfile; commit-stage failures also attempt index recovery. Inspect remaining changes and the original failure before retrying; do not reset unrelated files. |
| Commit prepared, branch or tag push incomplete           | Reconcile remote acceptance first. A clean prepared commit may equal upstream or be directly one commit ahead; rerunning the authorized release rechecks all four gates before retrying publication.                       |
| Remote publication accepted, installation refresh failed | Verify remote commit/tag and CD independently, then retry `mise run --force deploy` for the same checkout. An installation error does not undo publication.                                                                |
| Diverged branch, mismatched tag, or failed recovery      | Stop publication retries and report the conflicting state. Do not move published tags, overwrite assets, or rewrite history as an automatic repair.                                                                        |

## Documentation

- [Release workflow test](../../../dot/tests/test_release_workflow.py) checks the CD gate before attestation and publication.
- Companion skills: [dot-development](../dot-development/SKILL.md) (implementation and installation proof), [conventional-commit](../../../skills/conventional-commit/SKILL.md) (commit grammar).
