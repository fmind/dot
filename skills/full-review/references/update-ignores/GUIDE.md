---
name: update-ignores
description: "Audit and fix .gitignore, .ignore, .dockerignore, and tool excludes for the stack."
---

# Update Ignores

Align ignore and exclude configs with the repository's actual stack and tasks—edit ignore rules only, never deleting or untracking files ([full-review](../../SKILL.md)).

## Workflow

1. **Inventory**: check `git status --short --ignored`, existing ignore/tool excludes (`.gitignore`, `.ignore`, `.dockerignore`, `dprint.json`, `ruff.toml`, pytest/coverage), and manifests (`pyproject.toml`, `mise.toml`, `Dockerfile`, `*.tf`).
1. **Audit gitignore-syntax files**: [audit.py](scripts/audit.py) maps tracked, untracked, and collapsed-ignored paths to their deciding rule (pass `.ignore` explicitly so `.gitignore`-shadowed rules surface as unused):

   ```bash
   python3 -I ~/.agents/skills/full-review/references/update-ignores/scripts/audit.py            # every non-ignored .gitignore
   python3 -I ~/.agents/skills/full-review/references/update-ignores/scripts/audit.py .ignore --json
   ```

1. **Prune & add**: drop zero-hit foreign-stack, dead-tool, duplicate, and shadowed rules while keeping preventive secret/state rules (`.env`, `*.tfstate`, `*.pem`, `.terraform/`). Cover stack caches (`.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.ty_cache/`, `.coverage*`, `dist/`, `site/`, `node_modules/`); keep personal OS/editor noise in `~/.config/git/ignore` (`chezmoi source-path ~/.config/git/ignore`).
1. **Keep `.ignore` to search noise**: list only low-signal tracked files (locks, generated schemas, snapshots, fixtures, minified/vendored assets)—never duplicate `.gitignore` or exclude Python tests/fixtures, which Ruff and ty also skip. Lead comment-capable files with their doc URL ([gitignore](https://git-scm.com/docs/gitignore), [ripgrep filtering](https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md#automatic-filtering)).
1. **Check non-gitignore excludes & verify**: test globs via `git ls-files -- ':(glob)<pattern>'` or `fd --glob '<pattern>'` (`.dockerignore` uses Go `filepath.Match` per [containerize](../../../docker/references/containerize/templates/.dockerignore)); rerun `audit.py`, verify `git ls-files -ci --exclude-standard` adds zero newly ignored tracked files, and report changes.

## Gotchas

- **`.ignore` & `RIPGREP_CONFIG_PATH` limits**: `audit.py` evaluates `.ignore` as `core.excludesFile`: `!` negations re-including gitignored files report `n/a`, and nested `.ignore` triggers a warning. Because `rg` reads `RIPGREP_CONFIG_PATH` and `.ignore` by default, run `rg --no-config -uuu` (or `fd -H`) when auditing lockfiles or ignored paths.
- **Ask before untracking**: ignore rules never untrack committed files.

## Documentation

- [gitignore](https://git-scm.com/docs/gitignore) · [git check-ignore](https://git-scm.com/docs/git-check-ignore) · [Docker build context](https://docs.docker.com/build/concepts/context/#dockerignore-files)
- Companion skills: [project-scaffolding](../../../project-scaffolding/references/bootstrap.md).
