---
name: agents-cli
description: "Google agent scaffolding, lifecycle, and official skill discovery."
---

# Agents CLI

Use Google’s `agents-cli` to scaffold, run, evaluate, and deploy agents on Google Cloud; [google-adk](../google-adk.md) owns Python ADK implementation inside that project.

## Workflow

1. **Install only the Python CLI** and inspect its current contract before scaffolding. Keep the compatible release pin aligned with the upstream skills you review. Its usage telemetry (1.8.0) is an opt-in experiment, off by default; do not enable it unless requested.
   ```bash
   uv tool install "google-agents-cli"
   agents-cli --version
   agents-cli --help
   ```
1. **Review the official skills** before using them. List the bundle and read each selected snapshot without installing it.
   ```bash
   skills add google/agents-cli --list
   skills use google/agents-cli@<name>
   ```
1. **Default to the full ADK scaffold** with Agent Runtime, Gateway-ready image, BigQuery analytics, GitHub Actions, Terraform and `AGENTS.md`. The CLI creates the project directory; `--skip-checks --yes` avoids interactive cloud setup. Rehearse in a fresh temporary directory using [scaffold qualification](references/scaffold-qualification.md) when the CLI version or option set changes.
   ```bash
   agents-cli create <name> --agent adk \
     --agent-guidance-filename AGENTS.md --agent-gateway --bq-analytics \
     --deployment-target agent_runtime --cicd-runner github_actions \
     --skip-checks --yes
   cd <name>
   skills add google/agents-cli --skill <name> -y
   skills list
   ```
   Running `skills add` after `cd` keeps the reviewed skill project-scoped; use the immutable reviewed snapshot per the vendor policy. Agent Runtime manages sessions internally: omit `--session-type` for this target. Use `--prototype` only when the user requests the reduced scaffold; `--adk` create quickstart also forces prototype mode. Existing projects retain their accepted architecture; preview enhancements from that project's working directory rather than replacing it with these new-project defaults, and move it to a newer CLI release with `agents-cli scaffold upgrade --dry-run` and a reviewed 3-way merge instead of regenerating it.
1. **Implement with [google-adk](../google-adk.md) in the generated app**: keep `agent.py`, `fast_api_app.py`, `agents-cli-manifest.yaml`, and the generated tests. Define type-hinted tools with narrow permissions and explicit error contracts; keep prompts and model choices in reviewable source.
1. **Run code checks and offline tests** before a smoke prompt. Inspect generated imports first: BigQuery-enabled code can create a dataset while importing `app.agent` if `GOOGLE_CLOUD_PROJECT` is set. Mock external clients and isolate credentials in offline tests; preparing a full scaffold does not authorize those cloud writes.
   ```bash
   agents-cli install --locked
   agents-cli lint
   uv run pytest -q tests/unit
   # Explicitly authorized provider smoke test:
   agents-cli run "hello"
   ```
1. **Evaluate behavior**: keep a versioned dataset with expected responses, tool trajectories, and safety cases; run `agents-cli eval run`, compare the candidate with its immutable baseline, and record cost, repetitions, and uncertainty.
1. **Instrument the candidate** with OpenTelemetry traces and structured logs per [observability](../../../observability/SKILL.md). Exclude prompt, completion, secret, and personal data bodies unless a reviewed policy explicitly permits them. Export from `agents-cli run` or `playground` only when authorized, with `--otel-to-cloud`; 1.7.0 removed `--trace-to-cloud`.
1. **Review deployment first**: from the intended project's directory, preview a target with `agents-cli scaffold enhance . --deployment-target <agent_runtime|cloud_run|gke> --skip-checks --yes --dry-run`, inspect generated infrastructure and IAM (its Terraform requires 1.11 or later), then run `agents-cli deploy` only with explicit deployment approval. Verify the deployed agent through `agents-cli run --url <service-url> --mode <a2a|adk> "hello"`.

## Gotchas

- **Do not run `agents-cli setup`**: it installs skills globally by default. Use `uv tool install` for the Python CLI and the reviewed `skills` commands above for project-scoped skill installation.
- **Smoke tests are not evaluations**: `pytest` checks deterministic code, `agents-cli run` checks wiring once, and repeated eval cases measure agent behavior.
- **Scaffold quality**: replace dummy tests, remove blanket type ignores, and inspect prerelease observability dependencies before accepting the generated lock; follow the [generated Python profile](references/python-profile.md).
- **Preserve scaffold choices**: do not silently change its model, deployment target, session service, or generated layout while implementing a feature.
- **Full means selected features**: `--deployment-target` accepts `agent_runtime`, `cloud_run`, `gke`, or `none`; `agent_runtime` is the valid spelling, not `agnet_runtime`. Through 1.8.0, `--session-type` with Agent Runtime warns and is discarded; managed sessions are selected by the runtime environment. That session flag belongs to the `cloud_run` and `gke` container targets.
- **Gateway-ready is not routed**: `--agent-gateway` only adds the gateway's root-CA trust to the image. Routing egress needs an authorized `agents-cli deploy --agent-gateway-egress <gateway>` naming an existing gateway with `governedAccessPath=AGENT_TO_ANYWHERE`. Review deployment flags, IAM, analytics content collection and retention before an authorized deployment.
- **Use ADC**: use ADC locally and in production per [model-providers](../../../model-providers/SKILL.md), with a narrow runtime service account; use an AI Studio key only when explicitly requested.
- **Pin a named model**: avoid `-latest`; use a dated snapshot when reproducibility matters and document the reason for the chosen Flash or Pro model.
- **Protect public agents**: store secrets in Secret Manager, constrain tools, and add reviewed input and output controls per [threat-model](../../../threat-model/SKILL.md).

## Official Skills

Upstream: `google/agents-cli`, with separate workflow, scaffold, ADK code, evaluation, deployment, publishing, and observability selections. Use the commands above within the shared [vendor-skill policy](../../../agent-project/references/vendor-skills.md).

## Documentation

- [ADK](https://adk.dev/) · [google/agents-cli](https://github.com/google/agents-cli) · [Agent Runtime](https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale)
- Releases: [agents-cli](https://github.com/google/agents-cli/releases)
- Companion skills: [python-stack](../../../python-stack/references/foundation/GUIDE.md), [quality-assurance](../../../quality-assurance/SKILL.md), [observability](../../../observability/SKILL.md), [cloud-run](../../../cloud-run/SKILL.md), [Google catalog](../../../google-developer/SKILL.md), [prompt-design](../../../prompt-design/SKILL.md).
