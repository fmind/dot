# Antigravity SDK Setup and Configuration

## 1. Install and Authenticate

[`orchestrator.py`](../templates/orchestrator.py) pins `google-antigravity==0.1.23` (bundles a harness binary) on Python 3.14 via PEP 723 and treats warnings as errors—never silence upstream deprecations.

```bash
uv add google-antigravity==0.1.23
export GOOGLE_CLOUD_PROJECT=<project-id>  # optional: ANTIGRAVITY_MODEL, GOOGLE_CLOUD_LOCATION
uv run orchestrator.py <workspace>
```

**SDK runs bill GCP or Gemini API, never the Antigravity subscription.** Default to ADC (`gcloud auth application-default login` / [model-providers](../../../../model-providers/SKILL.md)) via `LocalAgentConfig(vertex=True, project=..., location=...)` + `VertexEndpoint` (high thinking) so exported keys cannot switch backends. When Developer API is explicitly requested, pass a scoped key to `LocalAgentConfig(vertex=False, api_key=...)` via `dot secret run` ([dot-cli](../../../../dot-cli/SKILL.md)) or secret manager (native fallback `GEMINI_API_KEY`; never export globally, commit, or fall back from ADC errors).

## 2. Orchestrate

- **Static over dynamic subagents**: prefer named `types.SubagentConfig` roles; `CapabilitiesConfig(enable_subagents=True)` self-clones with the parent's full toolset.
- **Subagent-scoped tools** (0.1.15+): functions in `SubagentConfig(tools=[...])` expose only to that subagent without registering on the root (contrary to older docs; duplicate names across callables raise `ValueError`). `SubagentConfig.capabilities` defaults to read-only built-ins; `model=` overrides the model.
- **Typed results**: check `response.stop_reason` and validate `await response.structured_output()` (`None` when missing) via `Model.model_validate(...)`.
- **Resume**: set `conversation_id` (>=32 alphanumeric/hyphen chars, no underscores), `session_continuation_mode` (`CREATE_ONLY`, `CREATE_OR_RESUME`, `RESUME`), and `save_dir`.

## 3. Bound the Run

- **Policies gate tools**: `policy.allow`, `deny`, `ask_user`, `workspace_only`, `allow_all`, `deny_all` (tool-specific rules beat wildcards). Under `deny_all()`, explicitly `allow("<function_name>")` each custom tool (verified 0.1.20); default `confirm_run_command()` (0.1.23) blocks shell commands only.
- **Budgets gate volume**: `types.BudgetConfig(max_model_calls, max_tool_calls, max_input_tokens, max_output_tokens, max_total_tokens)` (`BudgetScope.FORWARD_LOOKING` counts post-resume spend only); pair with an `asyncio.timeout` deadline. Any `response.stop_reason` besides `UNSPECIFIED` (`MAX_*_EXCEEDED`, `QUOTA_EXHAUSTED`) means early termination.
- **Side effects and telemetry**: `RunCommandConfig` controls command timeout (600s default), `enable_daemons` (off), and `enable_sandbox` (off; warns if unsupported); `CompactionConfig(token_threshold=...)` and `tool_output_truncation_config` bound context; omit `BuiltinTools.SCHEDULE` unless persistent timers belong. Track `response.usage_metadata.total_token_count` and audit hooks ([observability](../../../../python-stack/references/observability.md)); never mask audit failures in `on_tool_error`.

## 4. Extend

- **Skills & MCP**: pass expanded paths (`skills_paths=[str(pathlib.Path("~/.agents/skills").expanduser())]`) for required skills only; wire MCP per [mcp-setup](../../../../agent-harnesses/references/mcp-setup.md).
- **Presets**: `.lightweight()` trims tools/prompts/subagents for small models; `.eval()` enables daemons + `allow_all()`—confine it to disposable workspaces.
- **Local & self-hosted models**: see [local-models.md](local-models.md).
