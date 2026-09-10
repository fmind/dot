# Full scaffold qualification

The preferred new-project profile is ADK + Agent Runtime + Gateway-ready image + BigQuery analytics + GitHub Actions + Terraform + `AGENTS.md`. This is a scaffold default, not cloud deployment or authorization to collect message content. Preserve explicit user choices and existing project architecture.

## Rehearse before adopting changed flags

```bash
agents-cli --version
agents-cli create --help
scaffold_dir=$(mktemp -d)
cd "$scaffold_dir"
# A fixture project prevents accidental inheritance of a real gcloud project.
GOOGLE_CLOUD_PROJECT=example-agent-project agents-cli create verified-agent \
  --agent adk --agent-guidance-filename AGENTS.md \
  --agent-gateway --bq-analytics \
  --deployment-target agent_runtime --cicd-runner github_actions \
  --skip-checks --yes
cd verified-agent
```

Do not use `--prototype` or the `--adk` create shortcut here: they select a reduced project without the requested infrastructure. `--skip-checks` skips cloud setup verification, but 1.5.0 still resolves the project from environment/gcloud for `.env`; use the fixture value during rehearsal. Do not source the generated `.env` or run agent code against that fixture project.

Inspect generated artifacts rather than trusting the success banner:

| Feature | Evidence |
| --- | --- |
| ADK app and guidance | `app/agent.py`, `AGENTS.md`, template identity in `agents-cli-manifest.yaml` |
| Agent Runtime | Manifest `create_params.deployment_target: agent_runtime`; runtime-aware session factory in `app/app_utils/services.py` |
| Gateway readiness | Manifest `agent_gateway: true`; Dockerfile accepts `AGENT_GATEWAY_ROOT_CERTIFICATES` and configures trust paths |
| BigQuery analytics | `BigQueryAgentAnalyticsPlugin` initialization in `app/agent.py`; this flag is not recorded in the 1.5.0 manifest |
| GitHub Actions | `.github/workflows/pr_checks.yaml`, `staging.yaml`, `deploy-to-prod.yaml`; manifest runner selection |
| Infrastructure | `deployment/terraform/` including CI identity/IAM and service definitions |

`--session-type agent_platform_sessions` is incompatible with `agent_runtime` in 1.5.0: the generator warns and stores `session_type: none`. This means no separately selected session backend, not absence of managed sessions. Generated services choose `VertexAiSessionService` when the runtime injects its agent-engine identity, falling back to in-memory locally; `SESSION_SERVICE_URI` can override that selection. Use the explicit session flag only with a compatible target when that architecture is requested.

## Qualification boundaries

On 2026-09-10, installed `agents-cli 1.5.0` created both the requested full option set and the corrected profile in disposable directories. The original warned about the ignored session flag; the corrected command completed without that warning. Generated source confirmed every feature above. `agents-cli install --locked` succeeded with Python 3.13.13; `agents-cli lint` passed Ruff, formatting, codespell and ty. The generated Python constraint remains `>=3.11,<3.14`. These checks retain upstream's file-wide `# ruff: noqa` in `app/agent.py`, blanket ty ignores and placeholder unit test; remove those quality gaps when implementing the project rather than treating scaffold lint as full qualification.

Before running tests or importing the app, inspect cloud effects: this template calls `bigquery.Client` and `create_dataset(..., exists_ok=True)` at import when a project is set. Its exception handler logs a warning and continues; that is not successful analytics wiring. Offline verification should use static inspection and mocked clients. `agents-cli install --locked` installs dependencies; unset an inherited `UV_PROJECT`, `VIRTUAL_ENV` and `COVERAGE_FILE` so verification uses the disposable project. Follow the generated Python profile for lint/type/test quality; dummy unit tests are not agent behavior proof.

For enhancements, `agents-cli scaffold enhance` always modifies the current directory. Its positional argument selects a template, not a destination project. Change into the intended isolated project first, use `--skip-checks --yes --dry-run`, review the proposed file changes, and then apply only the approved local scope. Preserve analytics and gateway configuration explicitly and inspect generated source again: the manifest does not persist every create flag. Avoid `--force` or `--prefer-new` as a substitute for resolving conflicts.

The scaffold does not prove provider execution, managed session persistence, gateway egress, BigQuery delivery, cloud permissions, CI success or deployment. Verify those only in the appropriate authorized environment.

Sources: [Google agents-cli](https://github.com/google/agents-cli), installed 1.5.0 `create --help`, `scaffold enhance --help`, generator source and disposable generated files. Recheck version-specific behavior when upgrading.
