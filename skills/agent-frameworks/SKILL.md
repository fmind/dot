---
name: agent-frameworks
description: "Build Python agents with Google ADK, LangChain, LangGraph, and agents-cli."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-frameworks
  created: "2026-09-16"
  updated: "2026-10-31"
---

# Agent Frameworks

Implement the existing or explicitly selected agent framework. Choosing a framework does not authorize provider calls, tracing exports, deployment, or installing every vendor skill.

## Workflow

1. **Keep the project's framework**: an existing agent stays on its framework unless the user asks to migrate it.
1. **Default new agents to Google ADK**: scaffold with agents-cli, then write SDK code per google-adk.
1. **Use LangGraph second**: choose it when ADK does not fit, for example a required non-Google stack, durable graph state, or interrupts ADK cannot express. Start from LangChain's `create_agent`, which returns a compiled LangGraph, and hand-write graph topology only where the standard loop falls short. LangChain alone is not a separate default.
1. **Read only the matching guide** and its required resources.

## Task guides

<!-- guides:start -->

- [agents-cli](references/agents-cli/GUIDE.md): Google agent scaffolding, lifecycle, and official skill discovery.
- [google-adk](references/google-adk.md): Google ADK agents, runners, tools, sessions, and evaluation.
- [langchain](references/langchain.md): LangChain model integration, agents, tools, retrieval, and middleware.
- [langgraph](references/langgraph.md): LangGraph state, persistence, streaming, interrupts, and durable execution.

<!-- guides:end -->
