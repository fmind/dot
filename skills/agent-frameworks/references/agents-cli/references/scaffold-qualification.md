# Full scaffold qualification

## Rehearse flag changes

Run `agents-cli --version && agents-cli create --help && cd "$(mktemp -d)"`, then invoke [GUIDE.md](../GUIDE.md#workflow)'s `agents-cli create` as `verified-agent` with `GOOGLE_CLOUD_PROJECT=example-agent-project` (`--skip-checks` skips cloud checks, not `.env` resolution from env/gcloud). Never source `.env` or run code against the fixture project.

## Checklist

1. **Inspect generated artifacts** (do not trust the banner):
   - **ADK & Agent Runtime**: `app/agent.py`, `AGENTS.md`, `agents-cli-manifest.yaml` (`deployment_target: agent_runtime`), `app/app_utils/services.py` session factory.
   - **Gateway & BigQuery**: `agent_gateway: true` + Dockerfile `AGENT_GATEWAY_ROOT_CERTIFICATES`; `BigQueryAgentAnalyticsPlugin` in `app/agent.py` (manifest may omit this flag).
   - **CI & Terraform**: `.github/workflows/{pr_checks,staging,deploy-to-prod}.yaml`, `deployment/terraform/` (CI IAM + services).
1. **Check session selection**: `--session-type` does not apply to `agent_runtime` (warns, records `session_type: none`); `services.py` selects `VertexAiSessionService` under injected runtime identity, in-memory locally, or `SESSION_SERVICE_URI`.
1. **Install and lint**: unset `UV_PROJECT`, `VIRTUAL_ENV`, and `COVERAGE_FILE`, run `agents-cli install --locked && agents-cli lint`, record the Terraform pin, and apply [generated Python profile](#generated-python-profile).
1. **Check import side effects**: `app/agent.py` calls `bigquery.Client` and `create_dataset(..., exists_ok=True)` at import when a project is set; verify offline via static inspection and mocks.
1. **Enhance in place carefully**:
   - Run `agents-cli scaffold enhance` from a clean Git tree (mutates `cwd`; its positional arg is a template name, not a path) with override flags + `--skip-checks --yes --dry-run` (exits 2 without overrides or `agents-cli-manifest.yaml`).
   - Real runs write `.agents-cli-original/` (blocking reruns until removed), and standard fallback copies the project—`.env` included—to `~/.agents-cli/backups/` even on `--dry-run` (delete rehearsal backups).
   - Re-pass analytics/gateway flags absent from the manifest, inspect diffs, and never pass `--force` or `--prefer-new`.

Verify provider calls, managed sessions, gateway egress, BigQuery delivery, IAM, CI, and deployment separately with authorization.

## Generated Python profile

Apply [python/foundation](../../../../python/references/foundation/GUIDE.md) checks without altering the generated layout:

1. **Check pins**: verify generator version, `requires-python`, ADK pin, and lockfile together.
1. **Unmask lint and dummy tests**: drop file-wide `# ruff: noqa` and blanket `[tool.ty.rules]` ignores, align `[tool.ty.environment] python-version` (generated `3.10`) to `requires-python`, fix root causes, replace placeholder tests with offline behavior tests, and wire commands via [mise](../../../../mise/SKILL.md).
1. **Audit prereleases and env vars**: inspect alpha/beta lockfile packages (e.g., observability resource detector) and warnings; use `GOOGLE_GENAI_USE_ENTERPRISE=true`, not `GOOGLE_GENAI_USE_VERTEXAI`.
1. **Harden GitHub Actions**: replace mutable tags (`@v4`/`@v2`) and `secrets: inherit` with 40-hex SHAs + version comments, `persist-credentials: false`, named secrets, and [jactionlint](../../../../github/SKILL.md) compliance.

Sources: [Google agents-cli](https://github.com/google/agents-cli) and [releases](https://github.com/google/agents-cli/releases).
