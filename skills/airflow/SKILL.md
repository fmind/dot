---
name: airflow
description: "Develop and test Airflow DAGs with the Astronomer astro CLI."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/airflow
  created: "2026-09-16"
  updated: "2026-10-04"
---

# Apache Airflow with Astronomer CLI

Use `astro` for local Apache Airflow development, DAG authoring, task testing, and debugging. [python-stack](../python-stack/SKILL.md) owns Python package conventions and [docker](../docker/SKILL.md) manages container runtimes.

Docker mode (the default) needs an existing Docker-compatible engine; run `dot doctor --headroom` before the first image pull or build. `--standalone` runs Airflow on the host without Docker. Workstation tools disable anonymous telemetry (`ASTRO_TELEMETRY_DISABLED=1`). Inspect the project's Airflow version before choosing service flags (`--api-server` and `--dag-processor` for Airflow 3; `--webserver` for Airflow 2).

## Workflow

1. **Inspect project layout**: confirm existing `dags/`, `Dockerfile`, `requirements.txt`, and `airflow_settings.yaml`.

1. **Start local environment**: `--no-browser` keeps the UI from opening.

   ```bash
   astro dev start --no-browser
   ```

1. **Validate DAG syntax and integrity**: parse DAG files to catch import and configuration errors without waiting for the scheduler.

   ```bash
   astro dev parse
   ```

1. **Test tasks and runs**: execute unit tests or run individual tasks directly inside the local environment.

   ```bash
   astro dev pytest
   astro dev run tasks test <dag_id> <task_id>
   ```

1. **Inspect service and task logs**: select the relevant component and keep `--follow` opt-in. Save large output to a private local artifact, check the command's exit status, then search for the DAG/run ID and error context instead of loading every line.

   ```bash
   astro dev logs --scheduler
   astro dev logs --api-server
   ```

1. **Stop or rebuild environment**: stop containers when done or rebuild when changing dependencies in `requirements.txt`.

   ```bash
   astro dev stop
   # After changing requirements.txt or Dockerfile:
   astro dev restart
   ```

## Gotchas

- **Top-level execution**: the scheduler evaluates top-level DAG code every few seconds; avoid database queries, API calls, or heavy computation outside operators.
- **Ports**: by default a shared reverse proxy serves each project at `http://<project>.localhost:6563` on random backend ports; `astro dev proxy status` lists each project's URL and Postgres port. `--no-proxy` restores fixed ports (`8080` for the API server or webserver, `5432` for Postgres), which can collide with local services.
- **Stateless task testing**: `astro dev run tasks test` runs a single task without recording state in the Airflow database; upstream task dependencies must be handled or mocked.
- **Version upgrades**: before moving to a newer Airflow or Astro Runtime (including Airflow 2 to 3), run `astro dev upgrade-test` (optionally `--airflow-version <version>`); it reports dependency changes, DAG import errors, and deprecation lint without modifying the project.

## Official Skills

Upstream: Astronomer Agent Skills at `astronomer/agents` (including Airflow 2-to-3 migration). Its `airflow` skill drives the `af` CLI and shares this skill's name: preview it, never install it under that name, and install only selected non-colliding skills under the shared [vendor-skill policy](../agent-project/references/vendor-skills.md#name-collisions).

## Documentation

- [Astronomer CLI Documentation](https://www.astronomer.io/docs/cli) · [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- Releases: [Astronomer CLI Releases](https://github.com/astronomer/astro-cli/releases)
- Companion skills: [python-stack](../python-stack/SKILL.md) (Python coding), [docker](../docker/SKILL.md) (containers), [duckdb](../duckdb/SKILL.md) (inspect task outputs).
