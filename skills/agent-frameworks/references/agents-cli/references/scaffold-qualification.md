# Full scaffold qualification

The full ADK scaffold is a new-project default, not deployment or content-logging approval. Preserve user choices and existing project architecture.

## Rehearse before adopting changed flags

```bash
agents-cli --version
agents-cli create --help
cd "$(mktemp -d)"
```

Run the [guide's](../GUIDE.md#workflow) `agents-cli create` as `verified-agent` prefixed with `GOOGLE_CLOUD_PROJECT=example-agent-project`, then `cd verified-agent` (`--skip-checks` skips cloud checks, not `.env` project resolution from env/gcloud). Never source `.env` or run code against the fixture project.

## Checklist

1. **Inspect generated artifacts** instead of trusting the banner:

   | Feature              | Evidence                                                                                                                |
   | -------------------- | ----------------------------------------------------------------------------------------------------------------------- |
   | ADK app and guidance | `app/agent.py`, `AGENTS.md`, template identity in `agents-cli-manifest.yaml`                                            |
   | Agent Runtime        | Manifest `create_params.deployment_target: agent_runtime`; runtime-aware session factory in `app/app_utils/services.py` |
   | Gateway readiness    | Manifest `agent_gateway: true`; Dockerfile accepts `AGENT_GATEWAY_ROOT_CERTIFICATES` and configures trust paths         |
   | BigQuery analytics   | `BigQueryAgentAnalyticsPlugin` in `app/agent.py` (manifest may omit this flag)                                          |
   | GitHub Actions       | `.github/workflows/pr_checks.yaml`, `staging.yaml`, `deploy-to-prod.yaml`; manifest runner                              |
   | Infrastructure       | `deployment/terraform/` including CI identity/IAM and service definitions                                               |

1. **Check session selection**: `--session-type` does not apply to `agent_runtime` (warns and records `session_type: none`); `services.py` picks `VertexAiSessionService` when runtime agent-engine identity is injected, in-memory locally, or `SESSION_SERVICE_URI`. Pass `--session-type` only on compatible targets.
1. **Install and lint**: unset `UV_PROJECT`, `VIRTUAL_ENV`, and `COVERAGE_FILE`, run `agents-cli install --locked` and `agents-cli lint`, record the Terraform version pin, and apply the [generated Python profile](#generated-python-profile).
1. **Check import side effects**: `app/agent.py` calls `bigquery.Client` and `create_dataset(..., exists_ok=True)` at import when a project is set, logging a warning on failure; verify offline with static inspection and mocks.
1. **Enhance in place carefully**: `agents-cli scaffold enhance` mutates the current directory (its positional argument names a template, not a path) from a clean Git tree. Pass override flags plus `--skip-checks --yes --dry-run` (exits 2 without an override or `agents-cli-manifest.yaml`). Real runs back up replaced files to `.agents-cli-original/` (blocking reruns until removed), and standard-mode fallback copies the project—including `.env`—to `~/.agents-cli/backups/` even on `--dry-run` (delete rehearsal backups). Re-specify analytics and gateway flags not persisted in the manifest, inspect diffs, and never use `--force` or `--prefer-new` to skip conflicts.

Verify provider calls, managed sessions, gateway egress, BigQuery delivery, IAM, CI, and deployment separately in an authorized environment.

## Generated Python profile

Apply [python-stack](../../../../python-stack/references/foundation/GUIDE.md) checks without replacing the generated layout:

1. **Check interpreter pins**: verify generator version, `requires-python`, ADK pin, and lockfile together.
1. **Unmask lint and replace dummy tests**: drop file-wide `# ruff: noqa` and blanket `[tool.ty.rules]` ignores, match `[tool.ty.environment] python-version` (generated as `3.10`) to `requires-python`, fix root causes, replace placeholder unit tests with offline behavior tests, and wire generated install/lint commands via [mise](../../../../mise/SKILL.md).
1. **Audit prereleases and env vars**: inspect `google-adk` and lockfile alpha/beta packages (such as the observability resource detector) plus import/deprecation warnings; use `GOOGLE_GENAI_USE_ENTERPRISE=true`, not deprecated `GOOGLE_GENAI_USE_VERTEXAI`.
1. **Harden GitHub Actions**: generated workflows use mutable tags (`actions/checkout@v4`, `google-github-actions/auth@v2`, `actions/setup-python@v4` rejected by jactionlint), keep credentials, and set `secrets: inherit`. Pin full release commit SHAs with version comments, set `persist-credentials: false`, pass named secrets only, and pass jactionlint per [github-actions](../../../../github-actions/SKILL.md).

Sources: [Google agents-cli](https://github.com/google/agents-cli) and [releases](https://github.com/google/agents-cli/releases).
