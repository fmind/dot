---
name: kaggle
description: "Operate Kaggle competitions, datasets, kernels, and submissions."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/kaggle
  created: "2026-09-16"
  updated: "2026-10-05"
---

# Kaggle CLI

Use `kaggle` for competition, dataset, kernel, and model operations from the shell. The official Kaggle skills document every command and metadata file; this skill owns authentication, download scope, and the authority boundary around submissions and publications.

## Workflow

1. **Resolve the account**: `kaggle auth login` (OAuth) or `KAGGLE_API_TOKEN` in the environment; the legacy `~/.kaggle/kaggle.json` still works. Never run `kaggle auth print-access-token` during ordinary work.
1. **Read before writing**: use bounded list/file commands and `kaggle competitions submission-limits <slug> --json` to inspect available data and submission limits. Read the competition's current rules separately with `kaggle competitions pages list list <slug> --content --page-name rules` (the repeated `list` is required by the CLI parser); these calls do not authorize accepting them.
1. **Download into an ignored directory**: accept the competition rules on the website first (the CLI returns 403 otherwise).

   ```bash
   kaggle competitions download <slug> -p data/
   kaggle datasets download <owner>/<name> -p data/ --unzip
   ```

1. **Track the timeline**: after accepting rules, list the page names with `kaggle competitions pages list list <slug>`, then read the deadlines with `--page-name timeline` (or `description` when no timeline page exists). Offer, or schedule when requested, Google Calendar reminders with [gws](../gws/SKILL.md): one week before the entry and team merger deadline, and on the final submission day.
1. **Inspect kernels before pushing**: `kaggle kernels init -p <dir>` writes `kernel-metadata.json`. Before an authorized `kaggle kernels push -p <dir>`, inspect the upload directory, target ID, data sources, `is_private`, accelerator, internet access, and run timeout: pushing uploads code and starts remote execution. Keep `is_private: true` unless public release was explicitly requested, and inspect `kaggle quota` before accelerator use. Verify with `kaggle kernels status <owner>/<slug>` and retrieve artifacts with `kaggle kernels output <owner>/<slug> -p out/`.
1. **Submit with authority**: a submission counts against the daily limit and shows on the leaderboard, so confirm the competition, file, and message first, then verify.

   ```bash
   kaggle competitions submit <slug> -f submission.csv -m "<message>"
   kaggle competitions submissions <slug>
   ```

1. **Publish with authority**: `kaggle datasets create -p <dir>` creates a private dataset unless `--public` is explicitly authorized. `kaggle datasets version -p <dir> -m "<message>"` updates an existing dataset and retains its visibility; it has no `--public` flag. Verify the target dataset's current visibility before uploading a version, and confirm the license and intended audience before either operation.

## Gotchas

- **Use `uv run` for pinned versions**: in a project that pins `kaggle`, call `uv run kaggle` so the pinned version runs instead of the global shim.
- **Silence warnings in scripts**: pass `-W` to silence the out-of-date warning so JSON output stays parseable.

## Official Skills

Upstream: `Kaggle/kaggle-cli` for command guidance and `Kaggle/kaggle-skills` for hackathon judging, agent exams, and Kaggle Benchmarks authoring. Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and install only the source relevant to the task.

## Documentation

- [Kaggle CLI](https://github.com/Kaggle/kaggle-cli) · [Kaggle API](https://www.kaggle.com/docs/api)
- Releases: [Kaggle CLI](https://github.com/Kaggle/kaggle-cli/releases)
- Companion skills: [gws](../gws/SKILL.md) (calendar reminders), [python-stack](../python-stack/references/foundation/GUIDE.md) (project layout), [duckdb](../duckdb/SKILL.md) (inspect downloads), [hf](../hf/SKILL.md) (Hub models and datasets), [colab](../colab/SKILL.md) (rented accelerators).
