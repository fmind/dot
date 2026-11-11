---
name: agents-cli
description: "Google agent scaffolding, lifecycle, and official skill discovery."
---

# Agents CLI

Scaffold, run, evaluate, and deploy Google Cloud agents with `agents-cli`; [google-adk](../google-adk.md) owns Python ADK code inside the project.

## Workflow

1. **Install the Python CLI with patched overrides**: align the release pin with reviewed upstream skills. While `google-agents-cli==1.13.0` caps `pyopenssl<26.2` (`cryptography<48`) and `litellm<1.97.0` upstream (4 HIGH CVEs), pass `--override` (or `[tool.uv] override-dependencies = ["cryptography>=50.0.0", "litellm>=1.100.4"]` in project `pyproject.toml`) rather than installing unpatched wheels globally. Usage telemetry defaults on since 1.9.0 (sending command metadata to the GCP project and Google); workstation mise sets `AGENTS_CLI_TELEMETRY=0`—keep it off elsewhere unless opted in (`agents-cli info` shows state).
   ```bash
   uv tool install --override <(printf 'cryptography>=50.0.0\nlitellm>=1.100.4\n') "google-agents-cli==1.13.0"
   agents-cli --version
   agents-cli --help
   ```
1. **Review official skills before use**: list the bundle and inspect each snapshot without installing.
   ```bash
   DISABLE_TELEMETRY=1 skills add google/agents-cli --list --json
   DISABLE_TELEMETRY=1 skills use <snapshot> --skill <name>
   ```
1. **Default to the full ADK scaffold** (Agent Runtime, Gateway-ready image, BigQuery analytics, GitHub Actions, Terraform, `AGENTS.md`): `--skip-checks --yes` skips interactive cloud setup. Rehearse in a temp directory per [scaffold qualification](references/scaffold-qualification.md) when the CLI version or flags change.
   ```bash
   agents-cli create <name> --agent adk_python \
     --agent-guidance-filename AGENTS.md --agent-gateway --bq-analytics \
     --deployment-target agent_runtime --cicd-runner github_actions \
     --skip-checks --yes
   cd <name>
   DISABLE_TELEMETRY=1 skills add <snapshot> --skill <name> -y
   DISABLE_TELEMETRY=1 skills list --json
   ```
   Running `skills add` inside `<name>` keeps the immutable reviewed snapshot project-scoped. Use `--prototype` only on request (`--adk` quickstart also forces it). Keep existing projects' architecture: [enhance in place](references/scaffold-qualification.md#checklist), and upgrade CLI releases via `agents-cli scaffold upgrade --dry-run` plus a reviewed 3-way merge rather than regenerating.
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
1. **Preview and gate deployment**: from the project root, preview with `agents-cli scaffold enhance --deployment-target <agent_runtime|cloud_run|gke> --skip-checks --yes --dry-run` (pass `--no-agent-gateway` on `cloud_run`/`gke`). Inspect Terraform (1.11+) and IAM: Agent Runtime (1.10+) and Cloud Run (1.13+) default to an Agent Identity principal unless created with `--agent-runtime-identity-default service_account` or `--cloud-run-identity-default service_account`. Run read-only `agents-cli deploy --dry-run` (Agent Runtime or, since 1.12, Cloud Run: checks APIs, IAM, `actAs`, secrets; exits 1 on failure), deploy only with explicit approval (A2A Agent Runtime deploys also register the card in Agent Registry / Gemini Enterprise), and verify via `agents-cli run --url <service-url> --mode <a2a|adk> "hello"`.

## Gotchas

- **Never run `agents-cli setup`**: it installs skills globally; use `uv tool install --override` and project-scoped `skills add` above.
- **Never run `agents-cli login`**: since 1.13 it runs `gcloud auth login --update-adc`, dropping configured ADC scopes and switching gcloud's active account (interactive `create` without `--skip-checks` offers it too). Use `dot login gcp`.
- **Vet extension skills**: `agents-cli extension add` (1.10+) copies skills to `.agents/skills/` (`--global` targets `~/.agents/skills`; never pass it), and `agents-cli install` restores them. Since 1.13, `google/agents-cli`, `google/adk-recipes`, and `google/agents-cli-extensions` skip trust prompts when release-pinned—review per [vendor-skill policy](../../../agent-project/references/vendor-skills.md) first. `agents-cli create` accepts recipe GitHub URLs (1.11+); `adk_python` (1.12+, `adk` alias) requires 1.12+ to enhance or upgrade.
- **Fix scaffold quality gaps**: apply the [generated Python profile](references/scaffold-qualification.md#generated-python-profile) before accepting the lock, without silently altering chosen model, target, session service, or layout.
- **Target-specific flags**: `--deployment-target` takes `agent_runtime`, `cloud_run`, `gke`, or `none`; omit `--session-type` on `agent_runtime`, which manages sessions internally ([session selection](references/scaffold-qualification.md#checklist)).
- **Gateway-ready is not routed**: `--agent-gateway` only adds root-CA trust. Egress routing requires authorized `agents-cli deploy --agent-gateway-egress <gateway>` on a gateway with `governedAccessPath=AGENT_TO_ANYWHERE`; review IAM and analytics collection/retention before deploying.
- **Auth, models, and security**: use ADC with a narrow runtime SA and pin dated/named models per [model-providers](../../../model-providers/SKILL.md#workflow) (AI Studio keys only on request; avoid `-latest`); store secrets in Secret Manager and harden public agents per [threat-model](../../../code-security/references/threat-model.md).

## Official Skills

Upstream `google/agents-cli` bundles workflow, scaffold, ADK, eval, deploy, publish, and observability skills; install project-scoped per [vendor-skill policy](../../../agent-project/references/vendor-skills.md).

## Documentation

- [ADK](https://adk.dev/) · [google/agents-cli](https://github.com/google/agents-cli) · [Agent Runtime](https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale)
- Releases: [agents-cli](https://github.com/google/agents-cli/releases)
- Companion skills: [python-stack](../../../python-stack/references/foundation/GUIDE.md), [observability](../../../python-stack/references/observability.md), [cloud-run](../../../cloud-run/SKILL.md), [google-developer](../../../gcloud/references/google-developer.md), [evaluation](../evaluation/GUIDE.md), [model-providers](../../../model-providers/SKILL.md).
