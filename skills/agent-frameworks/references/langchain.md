---
name: langchain
description: "LangChain create_agent, middleware, MCP tools, and structured output as LangGraph building blocks."
---

# LangChain

Use LangChain only as building blocks for a [langgraph](langgraph.md) agent: `create_agent` returns a compiled LangGraph, shaped with middleware. For long-horizon planning and subagents over a filesystem, evaluate [Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview) before hand-rolling it.

## Workflow

1. **Pin the v1 surface**: `uv add langchain` plus only the provider integrations in use, and check the installed version against the [changelog](https://docs.langchain.com/oss/python/releases/changelog). v1 moved legacy chains, retrievers, the indexing API, `hub`, and `langchain-community` exports to `langchain-classic` (`langchain_classic`).
1. **Assemble the agent**: `from langchain.agents import create_agent` with a `"provider:model"` string from project configuration; subclass `AgentState` for custom state (`state_schema=`) and pass per-run data through `context_schema=`, read as `runtime.context`, not the prompt.
1. **Contract the output**: `response_format=` with `ToolStrategy` or `ProviderStrategy` (`langchain.agents.structured_output`), read `result["structured_response"]`, and test `StructuredOutputValidationError` and `MultipleStructuredOutputsError`.
1. **Use built-in middleware first**: `langchain.agents.middleware` ships `ModelRetryMiddleware`, `ToolRetryMiddleware`, `ToolErrorMiddleware`, `ModelFallbackMiddleware`, `ModelCallLimitMiddleware`, `ToolCallLimitMiddleware` (the loop bound), `SummarizationMiddleware`, `PIIMiddleware`, and `HumanInTheLoopMiddleware(interrupt_on={"tool_name": True})`; set `interrupt_mode="per_call"` (since 1.4.6, the planned next default) to pause once per gated call with schema-checked answers.
1. **Attach MCP tools**: `uv add "langchain[mcp]>=1.4"` and `MCPAdapter`, building the agent inside `async with` so the tools keep their client; [mcp-setup](../../mcp-setup/SKILL.md) owns host configuration.
1. **Test deterministically**: script exact `AIMessage` tool calls with `GenericFakeChatModel` (`langchain_core.language_models.fake_chat_models`) and `InMemorySaver`. It lacks `bind_tools`, so `create_agent` with tools raises `NotImplementedError` until a test subclass returns `self` from `bind_tools`; create a fresh model per test because its message iterator is consumed.

## Gotchas

- **`create_react_agent` is deprecated**: v1 `create_agent` supersedes LangGraph's `create_react_agent`; treat code still importing it as pre-v1 and check its other imports.
- **`langchain.mcp` is beta and replaces `langchain-mcp-adapters`**: it raises `LangChainBetaWarning` once per process; port `MultiServerMCPClient` code with the [migration guide](https://docs.langchain.com/oss/python/migrate/langchain-mcp-adapters) rather than mixing both. A `str` target must be an `http(s)` URL because FastMCP resolves a string as a filesystem path first; never pass a model- or config-supplied string to a transport that could launch it.

## Official Skills

Upstream: [langchain-ai/langchain-skills](https://github.com/langchain-ai/langchain-skills) (`ecosystem-primer`, `langchain-fundamentals`, `langchain-middleware`, `langchain-rag`, `langchain-dependencies`). Apply the shared [vendor-skill policy](../../agent-project/references/vendor-skills.md) before a project-scoped installation.

## Documentation

- [Agents](https://docs.langchain.com/oss/python/langchain/agents) · [Middleware](https://docs.langchain.com/oss/python/langchain/middleware/overview) · [Structured output](https://docs.langchain.com/oss/python/langchain/structured-output) · [MCP](https://docs.langchain.com/oss/python/langchain/mcp) · [Unit testing](https://docs.langchain.com/oss/python/langchain/test/unit-testing)
- Releases: [changelog](https://docs.langchain.com/oss/python/releases/changelog) · [GitHub releases](https://github.com/langchain-ai/langchain/releases) · [v1 migration](https://docs.langchain.com/oss/python/migrate/langchain-v1)
- Live reference: the docs MCP endpoint `https://docs.langchain.com/mcp` answers for the current version.
- Companion skills: [system-prompts](system-prompts.md), [pydantic](../../python-stack/references/pydantic.md), [observability](../../python-stack/references/observability.md).
