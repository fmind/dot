---
name: agents-cli
description: Scaffold, evaluate, and deploy Google agent projects with agents-cli and its official skills. Use for new agent projects or the agents-cli lifecycle.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agents-cli
  created: "2026-09-06"
  updated: "2026-09-06"
---

# Agents CLI

Use Google’s `agents-cli` to scaffold, run, evaluate, and deploy agents on Google Cloud; [google-adk](../google-adk/SKILL.md) owns Python ADK implementation inside that project.

## Workflow

1. **Install only the Python CLI** and inspect its current contract before scaffolding. Keep the compatible release pin aligned with the upstream skills you review.
   ```bash
   uv tool install "google-agents-cli~=1.5.0"
   agents-cli --version
   agents-cli --help
   ```
1. **Review the official skills** before using them. List the bundle and read each selected snapshot without installing it.
   ```bash
   skills add google/agents-cli --list
   skills use google/agents-cli@<name>
   ```
1. **Start from a non-interactive prototype scaffold**; the CLI creates the project directory and `--yes` selects non-interactive mode. `--skip-checks` keeps scaffolding independent of cloud credential checks.
   ```bash
   agents-cli scaffold create <name> --agent adk --prototype --agent-guidance-filename AGENTS.md --skip-checks --yes
   cd <name>
   skills add google/agents-cli --skill <name> -y
   skills list
   ```
   Running `skills add` after `cd` keeps the reviewed skill project-scoped. Normalize existing code with `agents-cli scaffold enhance . --adk --prototype --yes`. Choose Agent Runtime for managed sessions, memory, registry, or user OAuth; choose Cloud Run for a self-managed container and network boundary.
1. **Implement with [google-adk](../google-adk/SKILL.md) in the generated app**: keep `agent.py`, `fast_api_app.py`, `agents-cli-manifest.yaml`, and the generated tests. Define type-hinted tools with narrow permissions and explicit error contracts; keep prompts and model choices in reviewable source.
1. **Run code checks and a smoke prompt** before behavioral evaluation.
   ```bash
   agents-cli install --locked
   agents-cli lint
   uv run pytest tests/unit
   # Explicitly authorized provider smoke test:
   agents-cli run "hello"
   ```
1. **Evaluate behavior**: keep a versioned dataset with expected responses, tool trajectories, and safety cases; run `agents-cli eval run`, compare the candidate with its immutable baseline, and record cost, repetitions, and uncertainty.
1. **Instrument the candidate** with OpenTelemetry traces and structured logs per [observability](../observability/SKILL.md). Exclude prompt, completion, secret, and personal data bodies unless a reviewed policy explicitly permits them.
1. **Review deployment first**: preview a target with `agents-cli scaffold enhance . --deployment-target <agent_runtime|cloud_run> --yes --dry-run`, inspect generated infrastructure and IAM, then run `agents-cli deploy` only with explicit deployment approval. Verify the deployed agent through `agents-cli run --url <service-url> --mode <a2a|adk> "hello"`.

## Gotchas

- **Do not run `agents-cli setup`**: it installs skills globally by default. Use `uv tool install` for the Python CLI and the reviewed `skills` commands above for project-scoped skill installation.
- **Smoke tests are not evaluations**: `pytest` checks deterministic code, `agents-cli run` checks wiring once, and repeated eval cases measure agent behavior.
- **Scaffold quality**: replace dummy tests, remove blanket type ignores, and inspect prerelease observability dependencies before accepting the generated lock; see [Python profiles](../python-stack/references/profiles.md).
- **Python compatibility**: the 1.5.0 scaffold requires Python `>=3.11,<3.14`; use Python 3.13 for this profile until the upstream dependency range changes.
- **Preserve scaffold choices**: do not silently change its model, deployment target, session service, or generated layout while implementing a feature.
- **Use ADC in production**: authenticate locally with Application Default Credentials and assign a narrow runtime service account; reserve API keys for local AI Studio prototypes.
- **Pin a named model**: avoid `-latest`; use a dated snapshot when reproducibility matters and document the reason for the chosen Flash or Pro model.
- **Protect public agents**: store secrets in Secret Manager, constrain tools, and add reviewed input and output controls per [threat-model](../threat-model/SKILL.md).

## Official Skills

Upstream: `google/agents-cli`, with separate workflow, scaffold, ADK code, evaluation, deployment, publishing, and observability selections. Use the commands above within the shared [vendor-skill policy](../agent-project/references/vendor-skills.md).

## Documentation

- [ADK](https://google.github.io/adk-docs/) · [google/agents-cli](https://github.com/google/agents-cli) · [Agent Runtime](https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale)
- Companion skills: [python-stack](../python-stack/SKILL.md), [quality-assurance](../quality-assurance/SKILL.md), [observability](../observability/SKILL.md), [cloud-run](../cloud-run/SKILL.md), [google-cloud](../google-cloud/SKILL.md), [prompt-design](../prompt-design/SKILL.md).
