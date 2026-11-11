---
name: agent-frameworks
description: "Build Python agents and system prompts with Google ADK, LangGraph, LangChain, and agents-cli."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-frameworks
  created: "2026-09-16"
  updated: "2026-11-10"
---

# Agent Frameworks

Use the project's existing or requested agent framework. Selecting a framework never authorizes provider calls, trace exports, deployment, or bulk vendor-skill installs.

## Workflow

1. **Keep the project's framework** unless the user asks to migrate.
1. **Default new agents to Google ADK**: scaffold with `agents-cli`, then implement per `google-adk`.
1. **Use LangGraph second**: pick it when ADK does not fit (non-Google stack, durable graph state, or custom interrupts). Use LangChain only as LangGraph building blocks: start with `create_agent` (a compiled LangGraph) and hand-write graph topology only where the standard loop falls short.
1. **Read only the matching guide** and its required resources.

## Task guides

<!-- guides:start -->

- [agents-cli](references/agents-cli/GUIDE.md): Google agent scaffolding, lifecycle, and official skill discovery.
- [google-adk](references/google-adk.md): Google ADK agents, runners, tools, sessions, and evaluation.
- [langchain](references/langchain.md): LangChain create_agent, middleware, MCP tools, and structured output for LangGraph.
- [langgraph](references/langgraph.md): LangGraph state, persistence, streaming, interrupts, and durable execution.
- [system-prompts](references/system-prompts.md): Application system prompt layering, rule wording, and validated structured output.

<!-- guides:end -->
