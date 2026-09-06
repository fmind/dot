# Antigravity SDK Setup and Configuration

## 1. Install and Authenticate

```bash
uv add google-antigravity                              # ships a ~126 MB harness binary; a git clone alone will not run
export GEMINI_API_KEY="<aistudio-key>"                 # Gemini Developer API, pay-as-you-go with a free tier
gcloud auth application-default login                  # Vertex path instead: LocalAgentConfig(vertex=True, project=..., location=...)
```

**Billing is the Gemini API, never the Antigravity subscription.** The SDK reads only `GEMINI_API_KEY` (or `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` with Vertex ADC); it never touches the OAuth login the `agy` CLI and IDE write to `~/.gemini`, so a Google AI Pro/Ultra plan grants it nothing. Without a key it fails closed at connect time with `AntigravityValidationError: A Gemini API key is required.` Keep the key in the environment or a secret manager per [sops-secrets](../sops-secrets/SKILL.md); never inline it in `LocalAgentConfig(api_key=...)` in committed code.

## 2. Orchestrate

[`references/orchestrator.py`](references/orchestrator.py) is a runnable parent-plus-two-subagent fan-out; the pieces that matter:

- **Static subagents**: `types.SubagentConfig(name, description, system_instructions, tools)` in `LocalAgentConfig(subagents=[...])` gives each worker its own context window and instructions. Prefer these — a named role is reviewable, whereas dynamic self-cloning is not.
- **Dynamic subagents**: `types.CapabilitiesConfig(enable_subagents=True)` alone lets the parent clone itself on demand, inheriting its toolset. Use it only for open-ended decomposition.
- **Register tools twice**: any callable a subagent uses must appear in the parent's `tools=[...]` as well, or the subagent starts without it.
- **Bound the fan-out**: `max_subagent_depth` caps nesting and `allowed_subagents` pins the roster; both belong in `CapabilitiesConfig`.
- **Typed results**: `response_schema=<pydantic model>` plus `await response.structured_output()` returns a validated `dict`, which is what makes a subagent's output safe to route programmatically.
- **Resume**: `conversation_id` with `session_continuation_mode` (`CREATE_ONLY`, `CREATE_OR_RESUME`, `RESUME`) and `save_dir` persists a long orchestration across processes.

## 3. Bound the Run

Two independent limits, and confusing them is how an unattended run burns a quota:

- **Policies decide _which_ tools run**: `policy.allow`, `deny`, `ask_user`, `workspace_only`, `allow_all`, `deny_all`. Custom Python functions and read-only built-ins are permitted by default; `run_command` and the write tools are not.
- **Budgets decide _how much_ runs**: `types.BudgetConfig(max_model_calls, max_tool_calls, max_input_tokens, max_output_tokens, max_total_tokens)`. This is the only hard stop on a delegating parent, so always set one.
- **Observe the cost**: `response.usage_metadata.total_token_count` per turn, and `hooks.pre_turn` / `post_turn` / `pre_tool_call_decide` / `post_tool_call` / `on_tool_error` / `on_session_end` for auditing per [observability](../observability/SKILL.md).

## 4. Extend

- **Tools**: plain functions with type hints and a docstring, passed to `tools=[...]`; filter built-ins with `CapabilitiesConfig(enabled_tools=...)` or `disabled_tools=...`.
- **Skills**: `skills_paths=["~/.agents/skills"]` loads this repository's `SKILL.md` catalog straight into an SDK agent, accepting either one skill directory or a parent of many.
- **MCP**: `mcp_servers=[types.McpStdioServer(name=..., command=..., args=[...], env={...})]` or `McpStreamableHttpServer`; server selection and host wiring live in [agent-mcp](../agent-mcp/SKILL.md).
- **Triggers**: `triggers.every(seconds, callback)` and `triggers.on_file_change(...)` drive background work without an external scheduler.
