---
name: antigravity-sdk
description: "Orchestrate multi-agent executions with the google-antigravity Python SDK: subagents, policies, token budgets, hooks, and MCP over Gemini. Use when building an Antigravity SDK agent."
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/antigravity-sdk
  created: "2026-09-03"
  updated: "2026-09-06"
---

# Antigravity SDK

Use `google-antigravity` when embedding the Antigravity harness itself provides value. [google-adk](../google-adk/SKILL.md) remains the default agent framework; [python-stack](../python-stack/SKILL.md) owns project conventions.

## Workflow

1. **Verify the installed SDK**: inspect the uv dependency and source before using its evolving API; distinguish the local SDK from the interactive `agy` CLI and hosted Interactions agent.
1. **Choose authentication**: Gemini API key (`ANTIGRAVITY_SDK_API_KEY` or `GEMINI_API_KEY`) or Vertex ADC through gcloud; read [setup and configuration](references/sdk-usage.md). The SDK uses Gemini API billing, not the CLI/IDE subscription.
1. **Bound the run**: explicitly select tools, policies, token/call budgets, subagent roster and depth, and result schemas; custom tools must enforce their own side-effect constraints.
1. **Implement the smallest topology**: adapt [orchestrator.py](references/orchestrator.py) only when independent workers are needed; follow the matching SDK skill for detailed APIs.
1. **Verify and observe**: use local fakes first, then authorized live access; record calls, denials, failures, usage, and termination. Do not infer completion from a running or detached process.

## Gotchas

- **`BuiltinTools.read_only()` omits `START_SUBAGENT`**: passing it verbatim as `enabled_tools` silently disables delegation, and the config then rejects `max_subagent_depth` at validation. Append `types.BuiltinTools.START_SUBAGENT` explicitly.
- **`policy.safe_defaults(handler)` takes a required handler** and routes every write to a human, so it blocks forever in an unattended run; compose explicit `allow`/`deny`/`workspace_only` policies for automation and reserve it for interactive tools.
- **Policies do not gate custom tools**: the engine only sees built-ins, so a custom function is executed as written — keep destructive work out of it.
- **Preview surface**: the SDK is pre-1.0 (`0.1.x`) and the published docs already lag the shipped API; verify signatures with `python -c "import inspect, google.antigravity"` before coding against a doc snippet.
- **Two products, one name**: this SDK runs the harness locally, while the `antigravity-preview-*` agent on the Gemini Interactions API runs in a Google-hosted sandbox and is billed and configured separately.

## Official Skills

Upstream: `Google-Antigravity/antigravity-sdk-python`; follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and select only the SDK surface used by the project.

## Documentation

- [SDK overview](https://antigravity.google/docs/sdk/overview/) · [Subagents](https://antigravity.google/docs/sdk/subagents/) · [Policies](https://antigravity.google/docs/sdk/policies/) · [Lifecycle](https://antigravity.google/docs/sdk/lifecycle/)
- [antigravity-sdk-python](https://github.com/Google-Antigravity/antigravity-sdk-python) · [antigravity-sdk-python skills](https://github.com/google-antigravity/antigravity-sdk-python/tree/main/skills) · [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Companion skills: [python-stack](../python-stack/SKILL.md), [google-adk](../google-adk/SKILL.md), [agent-mcp](../agent-mcp/SKILL.md), [prompt-design](../prompt-design/SKILL.md), [quality-assurance](../quality-assurance/SKILL.md), [observability](../observability/SKILL.md).
