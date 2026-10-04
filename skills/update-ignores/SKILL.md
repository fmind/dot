---
name: update-ignores
description: "Audit and fix .gitignore, .ignore, .dockerignore, and tool excludes for the repo's stack."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/update-ignores
  created: "2026-10-04"
  updated: "2026-10-04"
---

# Update Ignores

Make every ignore list describe the repository as it is: prune patterns that match nothing and belong to no tool in use, and add the ones its stack and tasks need. This edits ignore and exclude configuration only; it never deletes files or untracks them. [repository-maintenance](../repository-maintenance/SKILL.md) owns the broader upkeep pass.

## Workflow

1. **Inventory**: record `git status --short --ignored` as the baseline. List the ignore surfaces: every `.gitignore`, search-only `.ignore` (also `.rgignore`, `.fdignore`), `.dockerignore`, `.chezmoiignore` in a chezmoi source, and tool excludes such as dprint `excludes`, Ruff `extend-exclude`, pytest `norecursedirs`, and coverage `omit`. Detect the stack from manifests (`pyproject.toml`, `uv.lock`, `package.json`, `mise.toml`, `Dockerfile`, `*.tf`, docs configuration) and from what the repository's tasks write (caches, coverage, `dist/`, `site/`, `.terraform/`).
1. **Measure gitignore-syntax files**: the [audit script](scripts/audit.py) attributes each path (tracked, untracked, and ignored, with ignored directories collapsed) to the pattern that decides it, then prints hits, tracked hits, samples, in-file duplicates, and `.gitignore` lines repeated from the global excludes file. Audit `.ignore` explicitly; its `.gitignore`-shadowed patterns then show as unused, because ripgrep and fd already honor `.gitignore`.

   ```bash
   python -I ~/.agents/skills/update-ignores/scripts/audit.py            # every non-ignored .gitignore
   python -I ~/.agents/skills/update-ignores/scripts/audit.py .ignore --json
   ```

1. **Prune**: unused means "decides no current path", not "useless". Remove a pattern when it is unused and irrelevant to the stack (Node patterns in a Python-only repository, a renamed tool's cache), duplicated, or shadowed by a later pattern. Keep preventive patterns for credentials and state (`.env`, `*.tfstate`, `*.pem`, `.terraform/`) and for outputs the repository's own tasks create, even when absent now.
1. **Add**: cover what the stack and tasks generate (Python: `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.ty_cache/`, `.coverage*`, `htmlcov/`, `dist/`; docs: `site/`; Node: `node_modules/`), plus repository tool state the user does not track. Personal OS, editor, and agent-host state belongs in the global excludes file (`git config core.excludesFile`, default `~/.config/git/ignore`), not each repository; when dotfiles manage it, edit its source (`chezmoi source-path ~/.config/git/ignore`). Keep a repository copy only when other people clone it without that global file.
1. **Search-only `.ignore`**: list tracked files with no search value (lockfiles, generated profiles or schemas, snapshots, fixtures, minified assets, vendored data); never repeat `.gitignore`. Start comment-capable files with their documentation URL ([gitignore](https://git-scm.com/docs/gitignore), [ripgrep filtering](https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md#automatic-filtering)).
1. **Other syntaxes**: confirm each tool exclude still matches a path with `git ls-files -- ':(glob)<pattern>'` or `fd --glob '<pattern>'`. `.dockerignore` follows Go `filepath.Match` from the context root, not gitignore rules: use `**/` for depth and prefer an allowlist (`*`, then `!pyproject.toml`, `!uv.lock`, `!src/`) per [containerize](../containerize/SKILL.md).
1. **Verify**: re-run the audit; `git ls-files -ci --exclude-standard` must list no tracked file newly matched by an ignore rule (report any, never `git rm --cached` without approval); compare `git status --short --ignored` with the baseline so nothing becomes visible or hidden unexpectedly; run the repository's format check for edited configuration.
1. **Report**: patterns removed and added per file with the reason, kept-but-unused preventive patterns, and tracked files that match ignore rules.

## Gotchas

- **Last match wins**: Git attributes a path to its last matching pattern, so an earlier duplicate reads as unused, and a pattern after `!negation` can re-hide a file. Keep negations directly after the rule they refine.
- **Parent directories**: `dir/` excludes the directory itself, so `!dir/file` cannot re-include anything; use `dir/*` with `!dir/file`.
- **Anchoring**: a slash at the start or middle anchors to the file's directory (`/build`, `docs/site/`); a bare name such as `build/` matches at any depth.
- **Search-ignore limits**: the audit measures `.ignore` as Git's excludes file, below every `.gitignore` and anchored to the repository root. A `!` negation there re-includes gitignored paths for ripgrep and fd, which Git cannot measure, so the audit marks it `n/a`; never prune it for lacking hits. A nested `.ignore` gets a warning because its anchored patterns resolve from the root; check them with `rg --files` or `fd` instead.
- **Tracked files**: ignore rules never untrack. A tracked file matching a rule is either intended (`!` exception or vendored fixture) or a stale commit; ask before untracking.

## Documentation

- [gitignore](https://git-scm.com/docs/gitignore) · [git check-ignore](https://git-scm.com/docs/git-check-ignore) · [Docker build context](https://docs.docker.com/build/concepts/context/#dockerignore-files)
- Companion skills: [project-scaffolding](../project-scaffolding/references/bootstrap.md) (initial ignore files), [repository-maintenance](../repository-maintenance/SKILL.md) (full upkeep).
