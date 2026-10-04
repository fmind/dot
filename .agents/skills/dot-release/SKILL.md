---
name: dot-release
description: "Prepare, publish, recover, and verify fmind/dot releases through the repository task."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/dot-release
  created: "2026-07-08"
  updated: "2026-10-04"
---

# Dot Release

Use the checkout's release task as the single owner of preparation and publication. The global [release](../../../skills/git-delivery/references/release/GUIDE.md) skill owns generic versioning and publication verification; this skill owns dot's preconditions and recovery.

## Workflow

1. **Resolve the mode**: preparation, authorized release, or read-only reconciliation. The release command commits, pushes, and refreshes the installed CLI. An explicit `/dot-release` invocation or release request authorizes the whole flow below, including verification fixes, commits, and the push to `main`; loading this skill for reference or a review does not.
1. **Qualify first**: run [dot-verify](../dot-verify/SKILL.md) on the checkout and resolve its findings. Stop and report instead of releasing when a finding needs the user's decision or a gate stays red.
1. **Commit the candidate**: group verified work into logical [Conventional Commits](../../../skills/git-delivery/references/conventional-commit.md) (the changelog is generated from them), then `git fetch` and push `main` so HEAD equals upstream; pre-push hooks rerun the network checks. If upstream moved, integrate it without rewriting history only when its commits do not overlap the candidate; otherwise stop.
1. **Inspect preconditions**: a clean tree on the configured default branch with HEAD equal to the fetched upstream, and `git`, `git-cliff`, `mise`, and `uv` available. Defaults are `main` and `origin`; inspect the task's `--remote` and `--branch` arguments before assuming them. Preserve unrelated work when a precondition fails.
1. **Run the owner**: use the commands below from the repository. The task uses `uv run --frozen --directory dot python -m dot_tasks.release`, avoiding an installed CLI that may lag source.
1. **Read the result**: preparation updates `dot/pyproject.toml`, `CHANGELOG.md`, and `dot/uv.lock`, then runs only the gates CI and the pre-push hook do not: the starter templates (`mise run test:starters`, which resolves unlocked upstream packages and must pass before a tag is created), build, and the host completion check (`mise run check:completions`). Only those generated files may change. It then commits, creates the annotated tag, pushes both with `git push --atomic`, and runs `mise run --force deploy` to refresh the installed `dot` CLI.
1. **Verify delivery**: the tag triggers [cd.yml](../../../.github/workflows/cd.yml): a read-only `gate` job reruns `mise run all` and extracts the git-cliff notes; a `publish` job holding only `contents: write`, with no checkout, creates the GitHub release. Confirm with `gh run list --workflow cd.yml --branch <tag>` and `gh release view <tag>`. Local command success does not prove CD completion.

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
| Push accepted, installation refresh failed | Verify the remote commit, tag, and CD independently, then retry `mise run --force deploy`. An installation error does not undo publication.                    |
| CD gate failed on the tag                  | No release was created. Fix forward on `main` and release the next version; do not move published tags or rewrite history as an automatic repair.              |

## Documentation

- Releases: [fmind/dot](https://github.com/fmind/dot/releases) · [changelog](https://github.com/fmind/dot/blob/main/CHANGELOG.md)
- Companion skills: [dot-verify](../dot-verify/SKILL.md) (pre-release qualification), [dot-development](../dot-development/SKILL.md) (implementation and installation proof), [conventional-commit](../../../skills/git-delivery/references/conventional-commit.md) (commit grammar).
