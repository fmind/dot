# Full scaffold qualification

The guide's full ADK scaffold is a new-project default, not cloud deployment or authorization to collect message content. Preserve explicit user choices and existing project architecture.

## Rehearse before adopting changed flags

```bash
agents-cli --version
agents-cli create --help
cd "$(mktemp -d)"
```

Run the [guide's](../GUIDE.md#workflow) full-scaffold `agents-cli create` command there as `verified-agent`, prefixed with the fixture `GOOGLE_CLOUD_PROJECT=example-agent-project`, then `cd verified-agent`. The fixture prevents accidental inheritance of a real gcloud project: `--skip-checks` skips cloud setup verification, but the generator can still resolve the project from the environment or gcloud for `.env`. Do not source the generated `.env` or run agent code against that fixture project.

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
1. **Install and lint the disposable project**: unset an inherited `UV_PROJECT`, `VIRTUAL_ENV`, and `COVERAGE_FILE`, then run `agents-cli install --locked` and `agents-cli lint`. Record the generated Terraform requirement and apply the [generated Python profile](#generated-python-profile).
1. **Inspect cloud effects before importing the app**: this template calls `bigquery.Client` and `create_dataset(..., exists_ok=True)` at import when a project is set. Its exception handler logs a warning and continues; that is not successful analytics wiring. Offline verification uses static inspection and mocked clients.
1. **Enhance in place, deliberately**: `agents-cli scaffold enhance` always modifies the current directory, and its positional argument selects a template, not a destination project. Change into the intended isolated project first and run with the intended override flags plus `--skip-checks --yes --dry-run`; without an override flag or a saved `agents-cli-manifest.yaml` a dry run exits 2, so a project agents-cli did not create has no preview. There the real run moves each file it replaces to `.agents-cli-original/` and refuses to rerun while that folder exists, so start from a clean Git tree. A failed smart merge falls back to standard mode, which copies the project, `.env` included, to `~/.agents-cli/backups/` even during a dry run; delete a backup the rehearsal created. Review the proposed changes, then apply only the approved local scope. Preserve analytics and gateway configuration explicitly and inspect generated source again, because the manifest does not persist every create flag. Avoid `--force` or `--prefer-new` as a substitute for resolving conflicts.

The scaffold does not prove provider execution, managed session persistence, gateway egress, BigQuery delivery, cloud permissions, CI success, or deployment. Verify those only in the appropriate authorized environment.

## Generated Python profile

The generator owns layout and interpreter constraints. Apply [python-stack](../../../../python-stack/references/foundation/GUIDE.md) quality defaults selectively; do not replace the generated app with its library scaffold.

1. **Recheck the Python constraint**: inspect the selected generator version, generated Python range, ADK pin, and lock before carrying that constraint forward.
1. **Treat scaffold lint as partial**: remove upstream's file-wide `# ruff: noqa` and blanket `[tool.ty.rules]` suppressions, align `[tool.ty.environment] python-version` (generated as `3.10`) with `requires-python`, and fix each diagnostic at its source. Replace placeholder unit tests with offline behavior tests; dummy unit tests are not agent behavior proof. Keep the generated lint/install commands; wire local tasks to those commands through [mise](../../../../mise/SKILL.md).
1. **Inspect prerelease dependencies and import warnings**: check the generated `google-adk` pin and the lock for alpha or beta packages (the observability resource detector has shipped as an alpha), and recheck import and deprecation warnings on the selected release. Expect `GOOGLE_GENAI_USE_ENTERPRISE=true` rather than the deprecated `GOOGLE_GENAI_USE_VERTEXAI`.
1. **Harden the generated workflows**: they pin actions by tag (`actions/checkout@v4`, `google-github-actions/auth@v2`), keep checkout credentials, and use `secrets: inherit`, and jactionlint rejects `actions/setup-python@v4` as too old to run. Pin each action to the full commit SHA of its current release with a version comment, set `persist-credentials: false`, pass only named secrets, and rerun jactionlint per [github-actions](../../../../github-actions/SKILL.md).

Sources: [Google agents-cli](https://github.com/google/agents-cli) and its [release notes](https://github.com/google/agents-cli/releases); the selected release's `create --help`, `scaffold enhance --help`, and disposable generated files.
