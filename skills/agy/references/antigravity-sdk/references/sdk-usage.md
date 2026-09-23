# Antigravity SDK Setup and Configuration

## 1. Install and Authenticate

The standalone example selects Python 3.13 through PEP 723 metadata and was checked with warnings treated as errors. `google-antigravity==0.1.16` with `google-genai==2.22.0` fails that import check on Python 3.14; do not suppress the upstream deprecation warning or assume the broader SDK Python constraint proves compatibility.

```bash
uv add google-antigravity==0.1.16  # version exercised by the example; includes a harness binary
# Select the authorized ADC project; optionally override ANTIGRAVITY_MODEL/location.
export GOOGLE_CLOUD_PROJECT=<project-id>
uv run orchestrator.py <workspace>
```

**SDK calls use the selected Cloud or Gemini API billing, never the Antigravity subscription.** Reuse ADC for the authorized project; when authentication setup is requested, use `gcloud auth application-default login`. The example explicitly selects `LocalAgentConfig(vertex=True, project=..., location=...)` plus a `VertexEndpoint` with high thinking, so ambient Google API keys cannot choose the Developer API. It requires a project rather than silently charging the personal account; [model-providers](../../../../model-providers/SKILL.md) owns personal defaults and customer overrides.

For an explicitly requested Developer API integration, supply an application-scoped key directly to `LocalAgentConfig(vertex=False, api_key=...)` through [sops-secrets](../../../../sops-secrets/SKILL.md); the SDK's native fallback is `GEMINI_API_KEY`, while `ANTIGRAVITY_SDK_API_KEY` must be read and passed by application code. Do not export auto-discovered keys globally, inline them in committed code, or fall back to this path after ADC errors. The bundled example implements only the ADC path. Its local configuration smoke does not verify credentials, billing, model access, or inference.

## 2. Orchestrate

[`orchestrator.py`](../templates/orchestrator.py) is a runnable parent-plus-two-subagent fan-out; the pieces that matter:

- **Static subagents**: `types.SubagentConfig(name, description, system_instructions, tools)` in `LocalAgentConfig(subagents=[...])` gives each worker its own context window and instructions. Prefer these — a named role is reviewable, whereas dynamic self-cloning is not.
- **Dynamic subagents**: `types.CapabilitiesConfig(enable_subagents=True)` alone lets the parent clone itself on demand, inheriting its toolset. Use it only for open-ended decomposition.
- **Register tools twice**: any callable a subagent uses must appear in the parent's `tools=[...]` as well, or the subagent starts without it.
- **Bound the fan-out**: `max_subagent_depth` caps nesting and `allowed_subagents` pins the roster; both belong in `CapabilitiesConfig`.
- **Typed results**: `response_schema=<pydantic model>` plus `await response.structured_output()` extracts a parsed payload or `None`; validate it with `Model.model_validate(...)` and inspect `response.stop_reason` before routing it. A schema proves shape, not factual correctness or authority.
- **Resume**: `conversation_id` with `session_continuation_mode` (`CREATE_ONLY`, `CREATE_OR_RESUME`, `RESUME`) and `save_dir` persists a long orchestration across processes.

## 3. Bound the Run

Two independent limits, and confusing them is how an unattended run burns a quota:

- **Policies decide _which_ tools run**: `policy.allow`, `deny`, `ask_user`, `workspace_only`, `allow_all`, `deny_all`. In 0.1.16 the default `confirm_run_command()` policy denies shell commands but allows other built-ins, including writes. Set explicit capabilities and policies; custom Python tools enforce their own constraints.
- **Budgets decide _how much_ runs**: `types.BudgetConfig(max_model_calls, max_tool_calls, max_input_tokens, max_output_tokens, max_total_tokens)`. Set a budget and a caller deadline; a token limit does not bound wall time, and token usage is not a currency spending cap.
- **Observe the cost**: `response.usage_metadata.total_token_count` per turn, and lifecycle hooks for auditing per [observability](../../../../observability/SKILL.md). Never use `on_tool_error` to turn a failed audit tool into apparent success; fail the run or model failures in the typed result.

## 4. Extend

- **Tools**: plain functions with type hints and a docstring, passed to `tools=[...]`; filter built-ins with `CapabilitiesConfig(enabled_tools=...)` or `disabled_tools=...`.
- **Skills**: pass explicitly expanded paths, for example `skills_paths=[str(pathlib.Path("~/.agents/skills").expanduser())]`, and load only the required skills. A directory may contain one skill or a catalog.
- **MCP**: `mcp_servers=[types.McpStdioServer(name=..., command=..., args=[...], env={...})]` or `McpStreamableHttpServer`; server selection and host wiring live in [mcp-setup](../../../../mcp-setup/SKILL.md).
- **Triggers**: `triggers.every(seconds, callback)` and `triggers.on_file_change(...)` drive background work without an external scheduler.
