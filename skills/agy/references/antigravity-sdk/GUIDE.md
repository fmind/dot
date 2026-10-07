---
name: antigravity-sdk
description: "Python SDK orchestration, policy, subagents, and lifecycle."
---

# Antigravity SDK

Use `google-antigravity` when embedding the Antigravity harness itself provides value. [google-adk](../../../agent-frameworks/references/google-adk.md) remains the default agent framework; [python-stack](../../../python-stack/references/foundation/GUIDE.md) owns project conventions.

## Workflow

1. **Verify the installed SDK**: inspect the uv dependency and source before using its evolving API; distinguish the local SDK from the interactive `agy` CLI and hosted Interactions agent.
1. **Choose authentication**: default to GCP Agent Platform with ADC per [model-providers](../../../model-providers/SKILL.md); read [setup and configuration](references/sdk-usage.md). SDK calls use the selected Cloud or Gemini API billing, not the CLI/IDE subscription. API keys require explicit selection; never switch backends after an ADC failure.
1. **Bound the run**: explicitly select tools, policies, token/call budgets, subagent roster and depth, and result schemas; custom tools must enforce their own side-effect constraints.
1. **Implement the smallest topology**: adapt [orchestrator.py](templates/orchestrator.py) only when independent workers are needed; follow the matching SDK skill for detailed APIs.
1. **Verify and observe**: use local fakes first, then authorized live access; record calls, denials, failures, usage, and termination. Do not infer completion from a running or detached process.

## Gotchas

- **`BuiltinTools.read_only()` includes `SCHEDULE` and omits `START_SUBAGENT`**: filter out `SCHEDULE` for bounded runs. Passing the list verbatim as `enabled_tools` also silently disables delegation, and the config then rejects `max_subagent_depth` at validation; append `types.BuiltinTools.START_SUBAGENT` explicitly.
- **`policy.safe_defaults(handler)` takes a required handler** and routes every write to a human, so an interactive handler can stall an unattended run; compose explicit `allow`/`deny`/`workspace_only` policies for automation and reserve it for interactive tools.
- **Policies gate custom tools by function name**: `deny_all()` blocks a custom Python tool unless `allow("<name>")` follows it (verified in 0.1.20 against a local fake endpoint). An allowed tool runs with the process's privileges, so it must still enforce its own side-effect limits.
- **Startup fails closed**: `Agent` raises `ValueError` when write tools or MCP servers are active without a policy or decide hook. `LocalAgentConfig` defaults to `confirm_run_command()`; `LiteRTAgentConfig` and `LocalOpenAIAgentConfig` default to no policy, `.lightweight()` adds none, and `.eval()` sets `allow_all()`.
- **Defaults are autonomous**: since 0.1.18 the default toolset includes `schedule` (timers and cron jobs) plus `manage_task`, and excludes `ask_question`; `AgentBehavior.AUTONOMOUS` is the default. Disable `schedule` for bounded runs that must not leave background work.
- **Code against the installed version**: the example pins `google-antigravity==0.1.20`; locate the project version with `uv pip show google-antigravity` and read its source before coding against newer docs. Imports execute code and are not a passive inspection method.
- **Keep the example on Python 3.13**: the example selects Python 3.13. The reviewed `google-genai==2.27.0` dependency raises an `_UnionGenericAlias` deprecation warning on Python 3.14 under warnings-as-errors; recheck dependencies before widening the example's Python range.
- **Local OpenAI-compatible endpoints are unauthenticated**: `LocalOpenAIAgentConfig` sends no API key or `Authorization` header to its `base_url`, even with `OPENAI_API_KEY` set; front a remote endpoint with a loopback credential proxy per [local models](references/sdk-usage.md#5-local-and-openai-compatible-models).
- **Two products, one name**: this SDK runs the harness locally, while the `antigravity-preview-*` agent on the Gemini Interactions API runs in a Google-hosted sandbox and is billed and configured separately.

The example requires `GOOGLE_CLOUD_PROJECT` and ADC, defaults to `gemini-3.8-flash`, `global`, and high thinking, validates its workspace and final result, and logs event metadata rather than prompts. Its local configuration checks do not prove that the provider accepts the model or that the bundled harness enforces policies; exercise those separately within authorized access.

## Official Skills

Upstream: `Google-Antigravity/antigravity-sdk-python`; follow the shared [vendor-skill policy](../../../agent-project/references/vendor-skills.md) and select only the SDK surface used by the project.

## Documentation

- [SDK overview](https://antigravity.google/docs/sdk/overview/) · [Tools and skills](https://antigravity.google/docs/sdk/tools/) · [Subagents](https://antigravity.google/docs/sdk/subagents/) · [Policies](https://antigravity.google/docs/sdk/policies/) · [Structured output](https://antigravity.google/docs/sdk/structured-output/) · [Lifecycle](https://antigravity.google/docs/sdk/lifecycle/) · [Local models](https://antigravity.google/docs/sdk/local-models/)
- [antigravity-sdk-python](https://github.com/Google-Antigravity/antigravity-sdk-python) · [antigravity-sdk-python skills](https://github.com/google-antigravity/antigravity-sdk-python/tree/main/skills) · [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Releases: [antigravity-sdk-python](https://github.com/google-antigravity/antigravity-sdk-python/releases) · [SDK changelog](https://antigravity.google/docs/changelog) (it can lag PyPI; 0.1.20 was current on 2026-10-03 while the changelog listed 0.1.18)
- Companion skills: [python-stack](../../../python-stack/references/foundation/GUIDE.md), [google-adk](../../../agent-frameworks/references/google-adk.md), [mcp-setup](../../../mcp-setup/SKILL.md), [system-prompts](../../../system-prompts/SKILL.md), [quality-assurance](../../../quality-assurance/SKILL.md), [observability](../../../observability/SKILL.md).
