---
name: update-ignores
description: "Audit and fix .gitignore, .ignore, .dockerignore, and tool excludes for the stack."
---

# Update Ignores

Align ignore and exclude configs with the repository's actual stack and tasks—edit ignore rules only, never deleting or untracking files ([full-review](../../SKILL.md)).

## Workflow

1. **Inventory**: baseline `git status --short --ignored`; list `.gitignore`, `.ignore`/`.rgignore`/`.fdignore`, `.dockerignore`, `.chezmoiignore`, and tool excludes (dprint `excludes`, Ruff `extend-exclude`, pytest `norecursedirs`, coverage `omit`); infer stack/task outputs from manifests (`pyproject.toml`, `uv.lock`, `package.json`, `mise.toml`, `Dockerfile`, `*.tf`, docs configs).
1. **Audit gitignore-syntax files**: [audit.py](scripts/audit.py) maps tracked, untracked, and collapsed-ignored paths to their deciding rule (resolving relative `core.excludesFile` from repo root), flagging zero-hit, duplicate, and global-duplicate rules; pass `.ignore` explicitly so `.gitignore`-shadowed rules surface as unused:

   ```bash
   python -I ~/.agents/skills/full-review/references/update-ignores/scripts/audit.py            # every non-ignored .gitignore
   python -I ~/.agents/skills/full-review/references/update-ignores/scripts/audit.py .ignore --json
   ```

1. **Prune & add**: drop zero-hit rules from foreign stacks, dead tools, duplicates, or shadowed lines while keeping preventive secret/state/task-output rules (`.env`, `*.tfstate`, `*.pem`, `.terraform/`). Cover stack outputs (Python: `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.ty_cache/`, `.coverage*`, `htmlcov/`, `dist/`; docs: `site/`; Node: `node_modules/`); keep personal OS/editor/harness noise in global `core.excludesFile` (`~/.config/git/ignore` via `chezmoi source-path ~/.config/git/ignore`) unless external cloners need it.
1. **Keep `.ignore` to search noise**: list only low-signal tracked files (locks, generated schemas, snapshots, data fixtures, minified/vendored assets)—never duplicate `.gitignore` or list Python test/fixture source, which Ruff and ty also skip. Lead comment-capable files with their doc URL ([gitignore](https://git-scm.com/docs/gitignore), [ripgrep filtering](https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md#automatic-filtering)).
1. **Check non-gitignore excludes**: test globs via `git ls-files -- ':(glob)<pattern>'` or `fd --glob '<pattern>'`; `.dockerignore` uses Go `filepath.Match` (`**/` for depth) per the [containerize](../../../docker/references/containerize/templates/.dockerignore) denylist (preserving build-required `README.md` and `LICENSE`).
1. **Verify**: rerun `audit.py`, confirm `git ls-files -ci --exclude-standard` adds no newly ignored tracked files and `git status --short --ignored` matches baseline, and report pruned, added, kept-preventive, and tracked-matching rules.

## Gotchas

- **`.ignore` emulation limits**: `audit.py` evaluates `.ignore` as `core.excludesFile` (root-anchored, below `.gitignore`): `!` negations re-including gitignored paths for `rg`/`fd` report `n/a` (never prune for zero hits), and nested `.ignore` files trigger a warning—verify those with `rg --files` or `fd`.
- **Ask before untracking**: ignore rules never untrack committed files.

## Documentation

- [gitignore](https://git-scm.com/docs/gitignore) · [git check-ignore](https://git-scm.com/docs/git-check-ignore) · [Docker build context](https://docs.docker.com/build/concepts/context/#dockerignore-files)
- Companion skills: [project-scaffolding](../../../project-scaffolding/references/bootstrap.md).
