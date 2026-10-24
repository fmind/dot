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

Do not use `--prototype` or the `--adk` create shortcut here: they select a reduced project without the requested infrastructure. `--skip-checks` skips cloud setup verification, but the generator can still resolve the project from the environment or gcloud for `.env`; use the fixture value during rehearsal. Do not source the generated `.env` or run agent code against that fixture project.

## Checklist

1. **Inspect generated artifacts** rather than trusting the success banner:

   | Feature              | Evidence                                                                                                                |
   | -------------------- | ----------------------------------------------------------------------------------------------------------------------- |
   | ADK app and guidance | `app/agent.py`, `AGENTS.md`, template identity in `agents-cli-manifest.yaml`                                            |
   | Agent Runtime        | Manifest `create_params.deployment_target: agent_runtime`; runtime-aware session factory in `app/app_utils/services.py` |
   | Gateway readiness    | Manifest `agent_gateway: true`; Dockerfile accepts `AGENT_GATEWAY_ROOT_CERTIFICATES` and configures trust paths         |
   | BigQuery analytics   | `BigQueryAgentAnalyticsPlugin` initialization in `app/agent.py`; the manifest may not record this flag                  |
   | GitHub Actions       | `.github/workflows/pr_checks.yaml`, `staging.yaml`, `deploy-to-prod.yaml`; manifest runner selection                    |
   | Infrastructure       | `deployment/terraform/` including CI identity/IAM and service definitions                                               |

1. **Check the session selection**: `--session-type` does not apply to `agent_runtime`; the generator warns and stores `session_type: none`. That means no separately selected session backend, not absence of managed sessions: generated services choose `VertexAiSessionService` when the runtime injects its agent-engine identity, fall back to in-memory locally, and accept a `SESSION_SERVICE_URI` override. Use the explicit session flag only with a compatible target when that architecture is requested.
1. **Install and lint the disposable project**: unset an inherited `UV_PROJECT`, `VIRTUAL_ENV`, and `COVERAGE_FILE`, then run `agents-cli install --locked` and `agents-cli lint`. Record the generated Python constraint, ADK pin, and Terraform requirement, and follow the [generated Python profile](python-profile.md) for lint, type, and test quality.
1. **Treat scaffold lint as partial**: remove upstream's file-wide `# ruff: noqa`, blanket ty ignores, and placeholder unit tests when implementing the project; dummy unit tests are not agent behavior proof.
1. **Inspect cloud effects before importing the app**: this template calls `bigquery.Client` and `create_dataset(..., exists_ok=True)` at import when a project is set. Its exception handler logs a warning and continues; that is not successful analytics wiring. Offline verification uses static inspection and mocked clients.
1. **Enhance in place, deliberately**: `agents-cli scaffold enhance` always modifies the current directory, and its positional argument selects a template, not a destination project. Change into the intended isolated project first, run with `--skip-checks --yes --dry-run`, review the proposed changes, then apply only the approved local scope. Preserve analytics and gateway configuration explicitly and inspect generated source again, because the manifest does not persist every create flag. Avoid `--force` or `--prefer-new` as a substitute for resolving conflicts.

The scaffold does not prove provider execution, managed session persistence, gateway egress, BigQuery delivery, cloud permissions, CI success, or deployment. Verify those only in the appropriate authorized environment.

Sources: [Google agents-cli](https://github.com/google/agents-cli) and its [release notes](https://github.com/google/agents-cli/releases); the selected release's `create --help`, `scaffold enhance --help`, and disposable generated files.
