---
name: antigravity-sdk
description: "Python SDK orchestration, policy, subagents, and lifecycle."
---

# Antigravity SDK

Embed the local Antigravity harness with `google-antigravity` when harness capabilities pay off; [google-adk](../../../agent-frameworks/references/google-adk.md) remains the default agent framework and [python-stack](../../../python-stack/references/foundation/GUIDE.md) owns project setup.

## Workflow

1. **Inspect without importing**: check `uv pip show google-antigravity` and read installed `.venv` source before coding (imports run code); keep the local SDK distinct from the `agy` CLI.
1. **Authenticate**: default to GCP Agent Platform with ADC per [model-providers](../../../model-providers/SKILL.md); see [sdk-usage.md](references/sdk-usage.md) for version pins, billing, explicit API keys, and [local/OpenAI-compatible models](references/sdk-usage.md#5-local-and-openai-compatible-models).
1. **Bound the run**: set explicit tools, policies, token/call budgets, subagent roster/depth, and output schemas, enforcing side-effect gates inside custom tools.
1. **Minimize topology**: adapt [orchestrator.py](templates/orchestrator.py) (`gemini-3.8-flash`, `global`, high thinking, metadata-only logging) only when isolated workers help.
1. **Verify**: test against local fakes before authorized live runs, recording calls, denials, errors, usage, and `stop_reason`.

## Gotchas

- **`BuiltinTools.read_only()` includes `SCHEDULE` and drops `INVOKE_SUBAGENT`**: strip `SCHEDULE`, and append `types.BuiltinTools.INVOKE_SUBAGENT` when delegating (otherwise subagents silently turn off and `max_subagent_depth` fails validation).
- **Avoid `policy.safe_defaults(handler)` unattended**: it requires a handler that prompts on writes; compose explicit `allow`/`deny`/`workspace_only` rules instead.
- **Default policy allows writes**: `LocalAgentConfig`, `LiteRTAgentConfig`, and `LocalOpenAIAgentConfig` (even `.lightweight()`) default to [`confirm_run_command()`](references/sdk-usage.md#3-bound-the-run), blocking shell commands while allowing file writes (`Agent` raises `ValueError` only on empty `policies=[]` with no decide hook).
- **Autonomous defaults**: `AgentBehavior.AUTONOMOUS` enables `schedule`, `run_workflow`, and `manage_task` while omitting `ask_question`.
- **Two products, one name**: `google-antigravity` runs locally, whereas Gemini Interactions API `antigravity-preview-*` runs in a hosted Google sandbox with separate billing/config.

## Official Skills

Select only needed `Google-Antigravity/antigravity-sdk-python` skills per [vendor-skill policy](../../../agent-project/references/vendor-skills.md).

## Documentation

- [SDK overview](https://antigravity.google/docs/sdk/overview/) · [Tools and skills](https://antigravity.google/docs/sdk/tools/) · [Subagents](https://antigravity.google/docs/sdk/subagents/) · [Policies](https://antigravity.google/docs/sdk/policies/) · [Structured output](https://antigravity.google/docs/sdk/structured-output/) · [Lifecycle](https://antigravity.google/docs/sdk/lifecycle/) · [Local models](https://antigravity.google/docs/sdk/local-models/)
- [antigravity-sdk-python](https://github.com/Google-Antigravity/antigravity-sdk-python) · [skills](https://github.com/google-antigravity/antigravity-sdk-python/tree/main/skills) · [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Releases: [PyPI history](https://pypi.org/project/google-antigravity/#history) · [SDK changelog](https://antigravity.google/docs/changelog) (`## Antigravity SDK`)
- Companion skills: [python-stack](../../../python-stack/references/foundation/GUIDE.md), [google-adk](../../../agent-frameworks/references/google-adk.md), [mcp-setup](../../../agent-harnesses/references/mcp-setup.md), [agent-frameworks](../../../agent-frameworks/SKILL.md), [observability](../../../python-stack/references/observability.md).
