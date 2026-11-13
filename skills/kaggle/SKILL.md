---
name: kaggle
description: "Operate Kaggle competitions, datasets, kernels, and submissions."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/kaggle
  created: "2026-09-16"
  updated: "2026-11-13"
---

# Kaggle CLI

Operate Kaggle competitions, datasets, kernels, and models via `kaggle` (auth, download bounds, and authority gates on submissions, remote runs, and publications).

## Workflow

1. **Verify account**: `kaggle auth login` (OAuth), env `KAGGLE_API_TOKEN`, or legacy `~/.kaggle/kaggle.json`; never run `kaggle auth print-access-token`.
1. **Inspect before downloading**: check bounded listings, `kaggle competitions submission-limits <slug> --json`, and `kaggle competitions pages <slug> list --content --page-name rules` (reading rules never authorizes accepting them).
1. **Download into gitignored `data/`** (accept competition rules in the browser first, else HTTP 403):

   ```bash
   kaggle competitions download <slug> -p data/ --unzip
   kaggle datasets download <owner>/<name> -p data/ --unzip
   ```

1. **Check deadlines**: inspect `kaggle competitions pages <slug> list` (`--page-name timeline`, else `description`) and offer—or schedule when asked—[gws](../gws/SKILL.md) Calendar reminders one week before entry/merger deadlines and on final submission day.
1. **Audit kernels before `push`**: `kaggle kernels init -p <dir>` creates `kernel-metadata.json`. Before authorized `kaggle kernels push -p <dir>`, verify upload files, target ID, data sources, `is_private: true` (default private), internet, `--accelerator`, `-t` timeout, `--no-run` (push executes immediately otherwise), and `kaggle quota`; check `kernels status <owner>/<slug>` and `kernels output <owner>/<slug> -p out/`.
1. **Authorize submissions** (each counts against daily caps and posts to the leaderboard; `--wait` exits non-zero on scoring error/timeout after consuming the slot, or check `competitions submission <ref>`):

   ```bash
   kaggle competitions submit <slug> -f submission.csv -m "<message>" --wait 900
   kaggle competitions submissions <slug> --format json --page-size 5
   ```

1. **Authorize dataset publications**: `kaggle datasets create -p <dir>` defaults to private unless `--public` is approved; `datasets version -p <dir> -m "<message>"` keeps existing visibility (verify first, confirm license/audience, and pass history-destroying `-d/--delete-old-versions` only when requested).

## Gotchas

- **Prefer `uv run kaggle`** when a project pins `kaggle` so the locked version runs over the global shim.
- **Strip import-time `Warning:` lines** before JSON parsing (`-W` takes effect after import-time auth checks).

## Official Skills

Upstream: `Kaggle/kaggle-cli` (CLI commands) and `Kaggle/kaggle-skills` (judging, exams, Kaggle Benchmarks), reviewed per [vendor-skill policy](../agent-project/references/vendor-skills.md).

## Documentation

- [Kaggle CLI](https://github.com/Kaggle/kaggle-cli) · [Kaggle API](https://www.kaggle.com/docs/api)
- Releases: [Kaggle CLI](https://github.com/Kaggle/kaggle-cli/releases)
- Companion skills: [gws](../gws/SKILL.md) (calendar reminders), [python-stack](../python-stack/references/foundation/GUIDE.md) (project layout), [duckdb](../duckdb/SKILL.md) (inspect downloads), [hf](../hf/SKILL.md) (Hub models and datasets), [colab](../colab/SKILL.md) (rented accelerators).
