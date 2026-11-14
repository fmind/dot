---
name: airflow
description: "Develop and test Airflow DAGs with the Astronomer astro CLI."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/airflow
  created: "2026-09-16"
  updated: "2026-11-14"
---

# Apache Airflow with Astronomer CLI

Develop, test, and debug local Airflow DAGs with `astro` ([python-stack](../python-stack/SKILL.md) owns Python packaging; [docker](../docker/SKILL.md) owns container runtimes).

Default Docker mode requires a running container engine—check `dot doctor --headroom` before first image pull/build (`--standalone` runs without Docker; workstation sets `ASTRO_TELEMETRY_DISABLED=1`). Check the project's Airflow major before selecting component flags (`--api-server` / `--dag-processor` on Airflow 3 vs `--webserver` on Airflow 2), and use `astro dev run` rather than interactive `astro dev bash`.

## Workflow

1. **Start without opening a browser**:
   ```bash
   astro dev start --no-browser
   ```
1. **Parse DAGs for import and config errors**:
   ```bash
   astro dev parse
   ```
1. **Run unit and single-task tests**:
   ```bash
   astro dev pytest
   astro dev run tasks test <dag_id> <task_id>
   ```
1. **Inspect component logs** (keep `--follow` opt-in):
   ```bash
   astro dev logs --scheduler
   astro dev logs --api-server
   ```
1. **Stop or rebuild** (restart after `requirements.txt` or `Dockerfile` edits):
   ```bash
   astro dev stop
   astro dev restart
   ```

## Gotchas

- **Use `airflow.sdk` on Airflow 3**: import `dag`, `task`, and `DAG` from `airflow.sdk`; `ruff check --select AIR3` catches removed Airflow 2 imports early.
- **Reverse-proxy URLs vs fixed ports**: projects default to `http://<project>.localhost:6563` over random backend ports (`astro dev proxy status`); `--no-proxy` binds fixed `8080` and `5432`, risking port collisions.
- **`tasks test` is stateless**: records nothing in the metadata DB, so mock or supply upstream inputs.
- **Qualify upgrades with `astro dev upgrade-test`** (`--airflow-version <version>`): writes dependency, import, and lint reports to `upgrade-test-<current>--<new>/` and temporarily appends `pytest-html` to `requirements.txt`; avoid `--fix` blindly since it applies unsafe Ruff fixes.

## Official Skills

Upstream: `astronomer/agents` (including Airflow 2→3 migration). Preview—never install—its colliding `airflow` skill (`af` CLI); install only non-colliding skills per [vendor-skill policy](../agent-project/references/vendor-skills.md#name-collisions).

## Documentation

- [Astronomer CLI Documentation](https://www.astronomer.io/docs/cli) · [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- Releases: [Astronomer CLI Releases](https://github.com/astronomer/astro-cli/releases)
- Companion skills: [python-stack](../python-stack/SKILL.md) (Python coding), [docker](../docker/SKILL.md) (containers), [duckdb](../duckdb/SKILL.md) (inspect task outputs).
