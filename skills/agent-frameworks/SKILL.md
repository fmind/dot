---
name: agent-frameworks
description: "Build and evaluate Python agents and system prompts with Google ADK, LangGraph, LangChain, and agents-cli."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-frameworks
  created: "2026-09-16"
  updated: "2026-11-17"
---

# Agent Frameworks

Use the project's existing or requested agent framework. Selecting a framework never authorizes provider calls, trace exports, deployment, or bulk vendor-skill installs.

## Workflow

1. **Keep the project's framework** unless the user asks to migrate.
1. **Pick the simplest tier that fits**:
   - **Direct SDK (Tier 1)**: start with async `google-genai` ([gcp-agent-platform](../model-providers/references/gcp-agent-platform.md)) for single structured calls or fixed chains.
   - **Google ADK (Tier 2, default for new agents)**: layer `google-adk>=2.14.1` on [python-stack](../python-stack/references/foundation/references/bootstrap.md) + [cloud-run](../cloud-run/SKILL.md) per [google-adk](references/google-adk.md); opt into [agents-cli](references/agents-cli/GUIDE.md) only when full enterprise scaffolds (Agent Runtime, Agent Gateway, Terraform, BigQuery analytics) are needed.
   - **LangGraph (Tier 3)**: use when ADK does not fit (non-Google stack, durable graph state, or custom interrupts), using [langchain](references/langchain.md) `create_agent` only as building blocks.
1. **Load matching guides & verify**: read the active framework guide plus [system-prompts](references/system-prompts.md) and [evaluation](references/evaluation/GUIDE.md) (plus [rag-and-vectors](references/rag-and-vectors.md) when retrieving), and audit non-trivial agent/retrieval designs with `fmind-review-agents` and `fmind-review-rag` ([subagent](../subagent/SKILL.md)).

## Task guides

<!-- guides:start -->

- [agents-cli](references/agents-cli/GUIDE.md): Google agent scaffolding, lifecycle, and official skill discovery.
- [evaluation](references/evaluation/GUIDE.md): Evaluate prompt, model, retrieval, and agent changes with graded multi-trial experiments.
- [google-adk](references/google-adk.md): Google ADK agents, runners, tools, sessions, and evaluation.
- [langchain](references/langchain.md): LangChain create_agent, middleware, MCP tools, and structured output for LangGraph.
- [langgraph](references/langgraph.md): LangGraph state, persistence, streaming, interrupts, and durable execution.
- [rag-and-vectors](references/rag-and-vectors.md): Build hybrid pgvector/DuckDB retrieval with tenant ACL pushdown, Gemini embeddings, and native multimodal inputs.
- [system-prompts](references/system-prompts.md): Design layered, cache-friendly system prompts, tool guardrails, and schema-validated outputs for LLM agents.

<!-- guides:end -->

## Documentation

- [Google ADK](https://adk.dev/) · [google/agents-cli](https://github.com/google/agents-cli) · [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) · [LangChain](https://docs.langchain.com/oss/python/langchain/overview) · [Gemini prompting](https://aistudio.google.com/docs/prompting-strategies) · [Claude prompting](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- Releases: [adk-python](https://github.com/google/adk-python/releases) · [langgraph](https://github.com/langchain-ai/langgraph/releases)
- Companions: [model-providers](../model-providers/SKILL.md), [agent-protocols](../agent-protocols/SKILL.md), [python-stack](../python-stack/SKILL.md), [code-security](../code-security/SKILL.md).
