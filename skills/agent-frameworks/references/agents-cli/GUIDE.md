---
name: agents-cli
description: "Scaffold, test, eval, and deploy enterprise ADK agents with agents-cli."
---

# Agents CLI

Opt-in enterprise scaffolding (Agent Runtime, Gateway, Terraform, BigQuery analytics) via `agents-cli`; new agents default to [google-adk](../google-adk.md) on [python/foundation](../../../python/references/foundation/references/bootstrap.md).

## Workflow

1. **Install with CVE override**: `google-agents-cli==1.14.0` caps `pyopenssl<26.2` (`cryptography<48`); pass `--override` (or `[tool.uv] override-dependencies = ["cryptography>=50.0.0"]`; omit `[lint]` which caps `ruff<0.16`). Keep `AGENTS_CLI_TELEMETRY=0` (`agents-cli info`):
   ```bash
   uv tool install --override <(printf 'cryptography>=50.0.0\n') "google-agents-cli==1.14.0" && agents-cli --version
   ```
1. **Scaffold or upgrade**: default to full ADK (`--skip-checks --yes`; rehearse flags per [scaffold qualification](references/scaffold-qualification.md)); vet `google/agents-cli` skills project-scoped via [vendor-skill policy](../../../agent-harnesses/references/vendor-skills.md):
   ```bash
   agents-cli create <name> --agent adk_python \
     --agent-guidance-filename AGENTS.md --agent-gateway --bq-analytics \
     --deployment-target agent_runtime --cicd-runner github_actions --skip-checks --yes
   ```
   Pass `--prototype` only on request (`--adk` also forces it). Enhance existing projects in place ([checklist](references/scaffold-qualification.md#checklist)) via `agents-cli scaffold upgrade --dry-run` + 3-way merge.
1. **Implement with [google-adk](../google-adk.md)**: preserve `agent.py`, `fast_api_app.py`, `agents-cli-manifest.yaml`, and generated tests; give tools strict types, narrow permissions, and explicit errors.
1. **Test offline first**: importing `app.agent` with `GOOGLE_CLOUD_PROJECT` set can create a BigQuery dataset ([cloud effects](references/scaffold-qualification.md#checklist)); mock clients and isolate credentials before authorized smoke runs:
   ```bash
   agents-cli install --locked && agents-cli lint && uv run pytest -q tests/unit
   agents-cli run "<domain tool-smoke prompt>"   # authorized tool/edge smoke
   ```
1. **Evaluate**: run `agents-cli eval run --dataset <cases.json> --output <dir>` (authorized), then `agents-cli eval compare <baseline.json> <candidate.json>` offline; `eval run`/`grade` (1.13+) exit 1 on errors (`--qps`), `thresholds:` misses, or `--fail-under METRIC=SCORE`.
1. **Instrument**: wire structlog + OTel ([observability](../../../python/references/observability.md)) without prompt/completion/secret/PII bodies; pass `--otel-to-cloud` only when authorized.
1. **Preview and gate deploy**: run `agents-cli scaffold enhance --deployment-target <agent_runtime|cloud_run|gke> --skip-checks --yes --dry-run` (`--no-agent-gateway` on `cloud_run`/`gke`), inspect Terraform/Identity (`--agent-runtime-identity-default service_account` / `--cloud-run-identity-default service_account`), run `agents-cli deploy --dry-run`, deploy only with approval (A2A registers Agent Registry), and verify via `agents-cli run --url <url> --mode <a2a|adk> "<smoke prompt>"`.

## Gotchas

- **Never run `agents-cli setup` or `agents-cli login`**: `setup` installs globally (use [vendor-skill policy](../../../agent-harnesses/references/vendor-skills.md); `extension add` without `--global` stays project-scoped); `login` overwrites ADC scopes (use `dot login gcp`).
- **Keep scaffold quality**: apply [generated Python profile](references/scaffold-qualification.md#generated-python-profile) without changing model/target; omit `--session-type` on `agent_runtime` ([checklist](references/scaffold-qualification.md#checklist)).
- **Gateway & security**: `--agent-gateway` adds root-CA trust only (egress needs `deploy --agent-gateway-egress <gw>` with approval); use ADC + narrow SA, verified GA models ([request-contracts](../request-contracts.md)), Secret Manager, and [threat-model](../../../code-security/references/threat-model.md).

## Documentation

- [ADK](https://adk.dev/) · [google/agents-cli](https://github.com/google/agents-cli) ([releases](https://github.com/google/agents-cli/releases)) · [Agent Runtime](https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale)
- Companions: [python/foundation](../../../python/references/foundation/GUIDE.md), [observability](../../../python/references/observability.md), [cloud-run](../../../gcloud/references/cloud-run/GUIDE.md), [google-developer](../../../gcloud/references/google-developer.md), [evaluation](../evaluation/GUIDE.md).
