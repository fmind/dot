---
name: shell
description: "Write and lint portable POSIX sh, Bash, and Fish scripts (shellcheck, shfmt, traps)."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/shell
  created: "2026-11-22"
  updated: "2026-11-24"
---

# Shell Scripting, Portability & Safety

Keep shell scripts small, strict, and auditable across `POSIX sh`, `bash`, `zsh`, and `fish` (bootstraps, entrypoints, Fish functions, git hooks, CI `run:` blocks). Once logic passes `~100` lines or needs retries, structured JSON/YAML parsing, or complex branching, graduate to a PEP 723 Python script ([python/script](../python/references/script/GUIDE.md)).

## Workflow

1. **Pick a dialect-true shebang and strict header**:
   - **Strict POSIX `sh`** (`dash`/Alpine/BSD): `#!/bin/sh` + `set -eu` (no bashisms: no `[[ ]]`, arrays, `pipefail`, `local` where strict portability applies, or `$'...'`).
   - **Bash**: `#!/usr/bin/env bash` + `set -euo pipefail`.
   - **Zsh**: `#!/usr/bin/env zsh` + `emulate -L zsh` + `set -euo pipefail` (syntax-check via `zsh -n`).
   - **Fish**: `#!/usr/bin/env fish` (never mix POSIX syntax; use `set -gx`—never `set -U`—inside tracked config files so persistent universal state is never mutated).
1. **Quote every expansion and protect paths**: wrap every variable and command substitution (`"${var}"`, `"$(cmd)"`), store argument lists in arrays `"${arr[@]}"` (or `set --` in `sh`) rather than space-delimited strings, pass `--` before variable paths (`rm -rf -- "${dir:?}/sub"`), and split `local out; out="$(cmd)"` so `local`/`export`/`readonly` never mask non-zero exits under `set -e`.
1. **Bound temp files, traps & non-TTY runs**: create temp dirs via `mktemp -d` with `trap cleanup EXIT; trap 'trap - EXIT; cleanup; trap - INT; kill -INT $$' INT; trap 'trap - EXIT; cleanup; trap - TERM; kill -TERM $$' TERM` (avoids double cleanup and preserves signal exits; guard unset vars under `set -u`), disable prompts (`--yes`, `</dev/null`), and keep operations idempotent (`ln -sfn`, pre-checks over blind `>>`).
1. **Eliminate injection & brittle parsing**: never interpolate variables into `eval`, `sh -c "..."`, or `sed`/`awk`—pass positional args (`sh -c 'cmd "$1"' _ "$arg"`), and verify checksums/signatures before running downloaded installers.
   - **Structured data**: parse JSON with `jq` and YAML with Go `yq` (`mikefarah/yq`, e.g. `yq -i '.key = strenv(VAL)' file.yml`—distinct from Python `kislyuk/yq`).
   - **Safe file iteration**: in POSIX `sh`, use `find ... -exec ... {} +` or safe globs; in Bash, use `while IFS= read -r -d '' f; do ...; done < <(find ... -print0)` (never `for f in $(ls ...)`).
1. **Verify with deterministic linters and syntax checks**:

   ```bash
   shellcheck -- <scripts...>
   shfmt -d -i 2 -s -- <scripts...>
   sh -n -- <posix-script>
   bash -n -- <bash-script>
   zsh -n -- <zsh-script>
   fish --no-config --no-execute -- <fish-script>
   fish --no-config -c 'fish_indent --check < <fish-script>'
   ```

   `-n` and `--no-execute` parse one script per invocation (loop over multiple files rather than passing a list). Enable optional `.shellcheckrc` checks like `enable=check-extra-masked-returns` where supported; project `shfmt`/`shellcheck` flags take precedence. Pin `shellcheck` and `shfmt` per project in `mise.toml` ([mise](../mise/SKILL.md)) and audit non-trivial scripts, hooks, or CI `run:` blocks with `fmind-review-shell` ([subagent](../subagent/SKILL.md)).

## Gotchas

- **`set -e` exit masking**: `set -e` is disabled inside `if`/`&&`/`||` conditions and function calls within them; check critical steps explicitly and collect background PIDs with `wait "$pid"`.
- **Empty globs, empty arrays, & leading-dash filenames**: unmatched globs pass literal `*` unless `shopt -s nullglob` (Bash) or `[ -e "$f" ] || continue` (POSIX) guards the loop; prefix relative globs (`./*`) or pass `--` so `-` filenames cannot become flags. On macOS Bash 3.2 under `set -u`, empty `"${arr[@]}"` errors—expand via `${arr[@]+"${arr[@]}"}`.
- **GNU vs BSD userland drift**: `sed -i`, `mktemp`, `date`, `readlink -f`, and `xargs -r` behave differently on macOS vs Linux; stick to POSIX flags or move cross-platform scripts to Python.

## Documentation

- [ShellCheck Wiki](https://www.shellcheck.net/wiki/) · [shfmt](https://github.com/mvdan/sh) · [POSIX Shell](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html) · [Fish docs](https://fishshell.com/docs/current/)
- Companions: [python/script](../python/references/script/GUIDE.md), [mise](../mise/SKILL.md), [github/ci-cd](../github/references/ci-cd/GUIDE.md), [subagent](../subagent/SKILL.md).
