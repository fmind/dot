---
name: langchain
description: "LangChain create_agent, middleware, MCP tools, and structured output for LangGraph."
---

# LangChain

Use LangChain only as [langgraph](langgraph.md) building blocks: `create_agent` compiles a middleware-shaped LangGraph. For filesystem planning and subagents, evaluate [Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview) before custom loops.

## Workflow

1. **Pin v1**: `uv add langchain` plus required provider packages, checking the [changelog](https://docs.langchain.com/oss/python/releases/changelog). Legacy chains, retrievers, indexing, `hub`, and `langchain-community` re-exports live in `langchain-classic` (`langchain_classic`).
1. **Assemble**: `from langchain.agents import create_agent` with configured `"provider:model"`, `state_schema=` (`AgentState` subclass), and `context_schema=` (read via `runtime.context`, not the prompt).
1. **Contract output**: pass `response_format=` (`ToolStrategy` or `ProviderStrategy` from `langchain.agents.structured_output`), read `result["structured_response"]`, and test `StructuredOutputValidationError` and `MultipleStructuredOutputsError`.
1. **Prefer built-in middleware** (`langchain.agents.middleware`): `ModelRetryMiddleware`, `ToolRetryMiddleware`, `ToolErrorMiddleware`, `ModelFallbackMiddleware`, `ModelCallLimitMiddleware`, `ToolCallLimitMiddleware` (loop cap), `SummarizationMiddleware`, `PIIMiddleware`, and `HumanInTheLoopMiddleware(interrupt_on={"tool_name": True}, interrupt_mode="per_call")` (1.4.6+; schema-checked per-call pause).
1. **Attach MCP tools**: `uv add "langchain[mcp]>=1.4"` and keep `MCPAdapter` inside `async with` so tools retain the client; [mcp-setup](../../agent-harnesses/references/mcp-setup.md) owns host registration.
1. **Test deterministically**: drive `GenericFakeChatModel` (`langchain_core.language_models.fake_chat_models`) with `InMemorySaver`, subclassing `bind_tools` to return `self` and instantiating a fresh model per test.

## Gotchas

- **`create_react_agent` is pre-v1**: migrate to `create_agent` and audit adjacent imports.
- **`langchain.mcp` is beta**: emits `LangChainBetaWarning` and replaces `langchain-mcp-adapters` ([migration guide](https://docs.langchain.com/oss/python/migrate/langchain-mcp-adapters); never mix both). Require `http(s)` URLs for string targets—FastMCP resolves strings as local paths first, so never pass untrusted strings to launching transports.

## Official Skills

Upstream: [langchain-ai/langchain-skills](https://github.com/langchain-ai/langchain-skills) (`ecosystem-primer`, `langchain-fundamentals`, `langchain-middleware`, `langchain-rag`, `langchain-dependencies`); vet per [vendor-skill policy](../../agent-project/references/vendor-skills.md).

## Documentation

- [Agents](https://docs.langchain.com/oss/python/langchain/agents) · [Middleware](https://docs.langchain.com/oss/python/langchain/middleware/overview) · [Structured output](https://docs.langchain.com/oss/python/langchain/structured-output) · [MCP](https://docs.langchain.com/oss/python/langchain/mcp) · [Unit testing](https://docs.langchain.com/oss/python/langchain/test/unit-testing)
- Releases: [changelog](https://docs.langchain.com/oss/python/releases/changelog) · [GitHub releases](https://github.com/langchain-ai/langchain/releases) · [v1 migration](https://docs.langchain.com/oss/python/migrate/langchain-v1)
- Live docs MCP: `https://docs.langchain.com/mcp`.
- Companion skills: [evaluation](evaluation/GUIDE.md), [pydantic](../../python-stack/references/pydantic.md), [observability](../../python-stack/references/observability.md).
