# Antigravity SDK Setup and Configuration

## 1. Install and Authenticate

The standalone example selects Python 3.13 through PEP 723 metadata and was checked with warnings treated as errors. `google-antigravity==0.1.20` with `google-genai==2.27.0` fails that import check on Python 3.14; do not suppress the upstream deprecation warning or assume the broader SDK Python constraint proves compatibility.

```bash
uv add google-antigravity==0.1.20  # version exercised by the example; includes a harness binary
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
- **Subagent-scoped tools**: since 0.1.15 a callable listed only in `SubagentConfig(tools=[...])` is collected for execution and exposed only to that subagent, keeping it out of the root context. The docs page still says to register it on the parent too; that works but widens the root toolset, and two different callables with the same name raise `ValueError`. `SubagentConfig.capabilities` defaults to read-only built-ins, and `model=` pins a per-subagent model name.
- **Bound the fan-out**: `max_subagent_depth` caps nesting and `allowed_subagents` pins the roster; both belong in `CapabilitiesConfig`.
- **Typed results**: `response_schema=<pydantic model>` plus `await response.structured_output()` extracts a parsed payload or `None`; validate it with `Model.model_validate(...)` and inspect `response.stop_reason` before routing it. A schema proves shape, not factual correctness or authority.
- **Resume**: `conversation_id` with `session_continuation_mode` (`CREATE_ONLY`, `CREATE_OR_RESUME`, `RESUME`) and `save_dir` persists a long orchestration across processes. The ID needs at least 32 characters of letters, digits, and hyphens (no underscores).

## 3. Bound the Run

Two independent limits, and confusing them is how an unattended run burns a quota:

- **Policies decide _which_ tools run**: `policy.allow`, `deny`, `ask_user`, `workspace_only`, `allow_all`, `deny_all`; a specific tool rule beats a wildcard. Rules match built-ins, MCP servers, and custom Python tools by name, so `deny_all()` needs an explicit `allow("<function_name>")` for each custom tool. In 0.1.20 the `LocalAgentConfig` default `confirm_run_command()` denies shell commands but allows every other tool, including writes. Set explicit capabilities and policies; an allowed custom tool still enforces its own constraints.
- **Budgets decide _how much_ runs**: `types.BudgetConfig(max_model_calls, max_tool_calls, max_input_tokens, max_output_tokens, max_total_tokens)`; `BudgetScope.FORWARD_LOOKING` counts only spend after a resume. Set a budget and a caller deadline; a token limit does not bound wall time, and token usage is not a currency spending cap. `response.stop_reason` reports `BUDGET_EXCEEDED` and other early stops.
- **Bound side effects**: `RunCommandConfig` sets the command timeout (600 seconds by default), `enable_daemons` (off), and `enable_sandbox` (off; startup warns when the OS cannot enforce it). `CompactionConfig(token_threshold=...)` replaces the deprecated compaction dials, and `tool_output_truncation_config` caps command output tokens. Disable `BuiltinTools.SCHEDULE` unless the run should leave timers or cron jobs behind.
- **Observe the cost**: `response.usage_metadata.total_token_count` per turn, and lifecycle hooks for auditing per [observability](../../../../observability/SKILL.md). Never use `on_tool_error` to turn a failed audit tool into apparent success; fail the run or model failures in the typed result.

## 4. Extend

- **Tools**: plain functions with type hints and a docstring, passed to `tools=[...]`; filter built-ins with `CapabilitiesConfig(enabled_tools=...)` or `disabled_tools=...`.
- **Skills**: pass explicitly expanded paths, for example `skills_paths=[str(pathlib.Path("~/.agents/skills").expanduser())]`, and load only the required skills. A directory may contain one skill or a catalog.
- **MCP**: `mcp_servers=[types.McpStdioServer(name=..., command=..., args=[...], env={...})]` or `McpStreamableHttpServer`; server selection and host wiring live in [mcp-setup](../../../../mcp-setup/SKILL.md).
- **Triggers**: `triggers.every(seconds, callback)` and `triggers.on_file_change(...)` drive background work without an external scheduler.
- **Presets**: `.lightweight()` trims tools, prompts, and subagents for small models; `.eval()` is a benchmark preset that enables daemons and sets `allow_all()`, so never use it outside a disposable workspace.

## 5. Local and OpenAI-Compatible Models

Per [Local models](https://antigravity.google/docs/sdk/local-models/), the SDK is the documented way to run the harness against local or self-hosted models. The `agy` CLI and desktop app use the Google-served model list (Gemini plus plan-gated third-party models); agy 1.2.x also parses an undocumented `customModels` setting, which is not a supported contract.

- **`LiteRTAgentConfig(model_path=...)`** runs a `.litertlm` checkpoint on-device through a managed loopback server, with `backend` (`gpu` default, `npu`, `cpu`), and applies `.lightweight()` automatically. The documented Gemma 4 26B A4B checkpoint downloads about 16.8 GB and needs about 24 GB of VRAM or unified memory; run `dot doctor --headroom` first.
- **`LocalOpenAIAgentConfig(model=..., base_url=...)`** targets an OpenAI-compatible server such as Ollama, LM Studio, or vLLM; call `.lightweight()` to trim built-in tools and instructions for small models. It does not target `litert-lm serve`.

```python
config = LocalOpenAIAgentConfig(
    model="gemma4:26b",
    base_url="http://localhost:11434/v1",
    workspaces=[workspace],
).lightweight()
```

Verified in the 0.1.20 source and against a loopback fake server (2026-10-03): the harness streams `POST {base_url}/chat/completions` with OpenAI function tools and sends only `base_url` and the model name, with no `Authorization` header even when `OPENAI_API_KEY` is set. Its `GemmaEndpoint` proto has no API key or header field, and a `ModelTarget` endpoint contributes only its `base_url`. For a remote, authenticated endpoint, run a loopback proxy (for example LiteLLM or a reverse proxy) that injects the credential from [sops-secrets](../../../../sops-secrets/SKILL.md) or `dot secret run`, and point `base_url` at it. Billing then follows the endpoint provider. Tool-calling and structured-output quality depend on the served model; exercise file, shell, and `response_schema` paths on a disposable workspace before relying on them.
