---
name: dot-release
description: "Prepare, publish, recover, and verify fmind/dot releases through the repository task."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/dot-release
  created: "2026-07-08"
  updated: "2026-10-07"
---

# Dot Release

Use the checkout's release task as the single owner of preparation and publication. The global [release](../../../skills/git-delivery/references/release/GUIDE.md) skill owns generic versioning and publication verification; this skill owns dot's preconditions and recovery.

## Workflow

1. **Confirm authority**: the release command commits, pushes, and refreshes the installed CLI. An explicit `/dot-release` invocation or release request authorizes the whole flow below, including verification fixes, commits, the push to `main`, and the delivery fixes and follow-up release below; loading this skill for reference, review, or reconciling a past release does not.
1. **Qualify first**: run [dot-verify](../dot-verify/SKILL.md) on the checkout and resolve its findings. Stop and report instead of releasing when a finding needs the user's decision or a gate stays red.
1. **Commit the candidate**: group verified work into logical [Conventional Commits](../../../skills/git-delivery/references/conventional-commit.md) (the changelog is generated from them), then `git fetch` and push `main` so HEAD equals upstream; pre-push hooks rerun the network checks and tests. If upstream moved, integrate it without rewriting history only when its commits do not overlap the candidate; otherwise stop.
1. **Know the preconditions**: the task stops before writing unless `dprint`, `git`, `git-cliff`, `mise`, and `uv` exist, the tree is clean on `--branch` (default `main`), HEAD equals the fetched `--remote` (default `origin`), and the next tag is absent locally; without new Conventional Commits it releases nothing. Preserve unrelated work when a precondition fails.
1. **Run the owner**: use the commands below from the repository; the task runs from source (`uv run --frozen --directory dot python -m dot_tasks.release`), not the possibly stale installed CLI.
1. **Read the result**: the task bumps `dot/pyproject.toml`, `CHANGELOG.md`, and `dot/uv.lock` (only those files may change), formats the changelog with dprint (CD rejects a tree its formatter changes, so this never depends on Git hooks), gates the bumped commit (`check:network`, which refreshes the vulnerability data CD rechecks, `test:starters`, which re-resolves unlocked upstream packages since CI ran, `build`, and the host-only `check:completions`), then commits with the Lefthook output visible, tags, pushes both with `git push --atomic`, and runs `mise run deploy`.
1. **Verify delivery**: the tag triggers [cd.yml](../../../.github/workflows/cd.yml): a read-only `gate` job reruns `mise run all` and extracts the git-cliff notes; a `publish` job holding only `contents: write`, with no checkout, creates the GitHub release. Confirm with `gh run list --workflow cd.yml --branch <tag>` and `gh release view <tag>`. Local command success does not prove CD completion.
1. **Monitor and fix CI/CD**: watch the release commit's CI run (including the macOS job) and the tag's CD run to completion with `gh run watch <id> --exit-status`. On failure, read `gh run view <id> --log-failed`, fix the root cause forward on `main` (never rerun to hide a flake), push, and watch CI again; a failed CD gate then needs the next release per [Recovery](#recovery). Repeat until CI is green and `gh release view <tag>` succeeds; stop and report when a fix needs the user's decision.

```bash
mise run release        # interactive release (after dot-verify)
mise run release -- -y  # non-interactive, within an authorized release
```

## Recovery

Inspect `git status --short`, the release commit, local tag, and remote state before retrying. [release.py](../../../dot/dot_tasks/release.py) owns the flow; its failure cases are exercised in [test_release.py](../../../dot/tests/test_release.py).

| Failure boundary                           | Next action                                                                                                                                                    |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Before the release commit                  | The command restores the version, changelog, and lockfile from HEAD with `git restore`. Fix the original failure, then rerun.                                  |
| Local tag already exists                   | Preflight stops before writing files. Delete the leftover tag with `git tag -d <tag>` after confirming it never reached the remote, then rerun.                |
| Commit and tag created, atomic push failed | Nothing reached the remote. Retry the push the error prints; if upstream moved, delete the local tag, reset the release commit, integrate upstream, and rerun. |
| Push accepted, installation refresh failed | Verify the remote commit, tag, and CD independently, then retry `mise run deploy`. An installation error does not undo publication.                            |
| CD gate failed on the tag                  | No release was created. Fix forward on `main` and release the next version; do not move published tags or rewrite history as an automatic repair.              |

## Documentation

- Releases: [fmind/dot](https://github.com/fmind/dot/releases) · [changelog](https://github.com/fmind/dot/blob/main/CHANGELOG.md)
- Companion skills: [dot-verify](../dot-verify/SKILL.md) (pre-release qualification), [dot-development](../dot-development/SKILL.md) (implementation and installation proof), [conventional-commit](../../../skills/git-delivery/references/conventional-commit.md) (commit grammar).
