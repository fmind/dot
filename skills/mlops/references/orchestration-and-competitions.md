---
name: orchestration-and-competitions
description: "Airflow DAGs with astro and Kaggle downloads, kernels, and submissions."
---

# Orchestration and Competitions

Pin project-specific workflow CLIs (`astro`, `kaggle`) in the project `mise.toml` or `uv` environment rather than globally (`ASTRO_TELEMETRY_DISABLED=1`, `uv run kaggle`).

## Apache Airflow (`astro`)

1. **Check headroom & version**: run `dot doctor --headroom` before container pulls; match Airflow 3 (`airflow.sdk` `dag`/`task`/`DAG`, `--api-server`/`--dag-processor`, `ruff check --select AIR3`) vs Airflow 2 (`--webserver`).
1. **Validate locally without a browser**:
   ```bash
   astro dev start --no-browser
   astro dev parse
   astro dev pytest
   astro dev run tasks test <dag_id> <task_id>
   ```
1. **Debug & stop cleanly**: `astro dev logs --scheduler` / `--api-server`, `astro dev restart` after `requirements.txt`/`Dockerfile` edits, and `astro dev stop`. Preview `astronomer/agents` vendor skills per [vendor-skill policy](../../agent-harnesses/references/vendor-skills.md) (avoid duplicating guidance already owned by `mlops`).

## Kaggle (`kaggle`)

1. **Auth & rules**: use `kaggle auth login` (OAuth), `KAGGLE_API_TOKEN`, or `~/.kaggle/kaggle.json` (never print tokens); check `kaggle competitions submission-limits <slug> --json` and accept competition rules in the browser before downloading into gitignored `data/`.
   ```bash
   kaggle competitions download <slug> -p data/ --unzip
   kaggle datasets download <owner>/<name> -p data/ --unzip
   ```
1. **Deadlines & kernels**: check `kaggle competitions pages <slug> list --page-name timeline`; before authorized `kaggle kernels push -p <dir>`, audit `kernel-metadata.json` (`is_private: true`, internet, accelerator, `-t` timeout, `--no-run`, `kaggle quota`).
1. **Authorize submissions & datasets**: submissions consume daily caps and `--wait` exits non-zero on scoring failures (`kaggle competitions submit <slug> -f submission.csv -m "<msg>" --wait 900`); keep `kaggle datasets create` private unless `--public` is approved. Strip import-time `Warning:` lines before JSON parsing.

## Documentation

- [Astronomer CLI](https://www.astronomer.io/docs/cli) · [Airflow Docs](https://airflow.apache.org/docs/) · [Kaggle CLI](https://github.com/Kaggle/kaggle-cli) · [Kaggle API](https://www.kaggle.com/docs/api)
