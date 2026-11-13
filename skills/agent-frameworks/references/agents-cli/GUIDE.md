---
name: agents-cli
description: "Google agent scaffolding, lifecycle, and official skill discovery."
---

# Agents CLI

Scaffold, run, evaluate, and deploy Google Cloud agents with `agents-cli`; [google-adk](../google-adk.md) owns Python ADK code inside the project.

## Workflow

1. **Install `agents-cli` with CVE overrides**: while `google-agents-cli==1.13.0` caps `pyopenssl<26.2` (`cryptography<48`) and `litellm<1.97.0` upstream, pass `--override` (or `[tool.uv] override-dependencies = ["cryptography>=50.0.0", "litellm>=1.100.4"]` in project `pyproject.toml`). Workstation mise sets `AGENTS_CLI_TELEMETRY=0`; keep it off elsewhere unless opted in (`agents-cli info` checks state).
   ```bash
   uv tool install --override <(printf 'cryptography>=50.0.0\nlitellm>=1.100.4\n') "google-agents-cli==1.13.0"
   agents-cli --version
   ```
1. **Default to the full ADK scaffold** (Agent Runtime, Gateway-ready image, BigQuery analytics, GitHub Actions, Terraform, `AGENTS.md`): `--skip-checks --yes` skips interactive cloud setup (rehearse flag changes in temp dirs per [scaffold qualification](references/scaffold-qualification.md)). Review upstream `google/agents-cli` skills project-scoped via [vendor-skill policy](../../../agent-project/references/vendor-skills.md) (never `agents-cli setup` or global installs):
   ```bash
   agents-cli create <name> --agent adk_python \
     --agent-guidance-filename AGENTS.md --agent-gateway --bq-analytics \
     --deployment-target agent_runtime --cicd-runner github_actions \
     --skip-checks --yes
   ```
   Use `--prototype` only on request (`--adk` quickstart also forces it). Keep existing projects' architecture ([enhance in place](references/scaffold-qualification.md#checklist)), upgrading via `agents-cli scaffold upgrade --dry-run` + 3-way merge.
1. **Implement with [google-adk](../google-adk.md)**: preserve `agent.py`, `fast_api_app.py`, `agents-cli-manifest.yaml`, and generated tests. Give tools strict types, narrow permissions, and explicit error contracts; keep prompts and model pins in source.
1. **Test offline first**: importing `app.agent` with `GOOGLE_CLOUD_PROJECT` set can create a BigQuery dataset ([cloud effects](references/scaffold-qualification.md#checklist)), so mock external clients and isolate credentials—scaffolding does not authorize cloud writes.
   ```bash
   agents-cli install --locked
   agents-cli lint
   uv run pytest -q tests/unit
   # Explicitly authorized provider smoke test:
   agents-cli run "hello"
   ```
1. **Evaluate behavior**: run `agents-cli eval run --dataset <versioned-cases.json> --output <results-dir>` on baseline and candidate (requires provider/GCP Eval Service authorization), then diff offline with `agents-cli eval compare <baseline.json> <candidate.json>`. Since 1.13, `eval run` and `eval grade` exit 1 on case errors (lower `--qps` on rate limits), config `thresholds:` misses, or `--fail-under METRIC=SCORE`; gate CI on the exit code.
1. **Instrument**: wire OpenTelemetry traces and structured logs per [observability](../../../python-stack/references/observability.md), omitting prompt, completion, secret, and PII bodies unless policy permits; pass `--otel-to-cloud` on `run` or `playground` only when authorized.
1. **Preview and gate deployment**: preview with `agents-cli scaffold enhance --deployment-target <agent_runtime|cloud_run|gke> --skip-checks --yes --dry-run` (pass `--no-agent-gateway` on `cloud_run`/`gke`). Inspect Terraform (1.11+) and Agent Identity defaults (pass `--agent-runtime-identity-default service_account` or `--cloud-run-identity-default service_account` to keep explicit service accounts). Run `agents-cli deploy --dry-run` first; deploy only with approval (A2A deploys register cards in Agent Registry), and verify via `agents-cli run --url <service-url> --mode <a2a|adk> "hello"`.

## Gotchas

- **Never run `agents-cli setup`**: installs skills globally; install project-scoped via [vendor-skill policy](../../../agent-project/references/vendor-skills.md) instead (`extension add` without `--global` stays project-scoped).
- **Never run `agents-cli login`**: overwrites configured ADC scopes (`gcloud auth login --update-adc`); use `dot login gcp`.
- **Keep scaffold quality**: apply [generated Python profile](references/scaffold-qualification.md#generated-python-profile) without altering chosen model/target; omit `--session-type` on `agent_runtime` ([session selection](references/scaffold-qualification.md#checklist)).
- **Gateway routing**: `--agent-gateway` adds root-CA trust only; egress routing requires `agents-cli deploy --agent-gateway-egress <gateway>` (`governedAccessPath=AGENT_TO_ANYWHERE`) with approval.
- **Auth, models, and security**: ADC + narrow runtime SA, dated models per [model-providers](../../../model-providers/SKILL.md#workflow), Secret Manager secrets, and [threat-model](../../../code-security/references/threat-model.md).

## Official Skills

Upstream `google/agents-cli` bundles workflow, scaffold, ADK, eval, deploy, publish, and observability skills; install project-scoped per [vendor-skill policy](../../../agent-project/references/vendor-skills.md).

## Documentation

- [ADK](https://adk.dev/) · [google/agents-cli](https://github.com/google/agents-cli) · [Agent Runtime](https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale)
- Releases: [agents-cli](https://github.com/google/agents-cli/releases)
- Companion skills: [python-stack](../../../python-stack/references/foundation/GUIDE.md), [observability](../../../python-stack/references/observability.md), [cloud-run](../../../cloud-run/SKILL.md), [google-developer](../../../gcloud/references/google-developer.md), [evaluation](../evaluation/GUIDE.md), [model-providers](../../../model-providers/SKILL.md).
