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
1. **Load matching guides & verify**: read the active framework guide plus [evaluation](references/evaluation/GUIDE.md) (and [rag-and-vectors](references/rag-and-vectors.md) when retrieving), and audit non-trivial agent/retrieval designs with `fmind-review-agents` and `fmind-review-rag` ([subagent](../subagent/SKILL.md)).

## System Prompts

[model-providers](../model-providers/SKILL.md#request-contracts) owns per-model request parameters; [task-prompts](../task-prompts/SKILL.md) owns coding-agent handoffs.

- **Layer by stability**: static system text and tool schemas first (maximizing prefix caching), then per-turn context, history, and user input, placing long documents before the question.
- **State each rule once, with its why**: drop CAPS, MUST, and legacy nudges ("if in doubt, use the tool") that current Claude and Gemini models over-trigger ([Google prompt design](https://ai.google.dev/gemini-api/docs/prompting-strategies), [Anthropic prompting](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)).
- **Require critical thinking and completeness**: instruct agents in positive terms to verify premises against grounded evidence, surface uncertainty rather than guessing, handle empty/boundary/failure cases, and finish deliverables end-to-end without shortcuts.
- **Enforce authority in code**: delimit retrieved text, tool outputs, and memory as untrusted data; gate permissions, spend, and destructive actions in runtime/tool code, never prompt-only.
- **Validate structured output and fail closed**: use native schemas (ADK `output_schema`, LangChain `response_format`, `google-genai` `response_schema`) with Pydantic validation; reject invalid payloads instead of repairing prose, and isolate prompt changes against [evaluation](references/evaluation/GUIDE.md).

## Task guides

<!-- guides:start -->

- [agents-cli](references/agents-cli/GUIDE.md): Google agent scaffolding, lifecycle, and official skill discovery.
- [evaluation](references/evaluation/GUIDE.md): Evaluate prompt, model, retrieval, and agent changes with graded multi-trial experiments.
- [google-adk](references/google-adk.md): Google ADK agents, runners, tools, sessions, and evaluation.
- [langchain](references/langchain.md): LangChain create_agent, middleware, MCP tools, and structured output for LangGraph.
- [langgraph](references/langgraph.md): LangGraph state, persistence, streaming, interrupts, and durable execution.
- [rag-and-vectors](references/rag-and-vectors.md): Build hybrid pgvector/DuckDB retrieval with tenant ACL pushdown, Gemini embeddings, and native multimodal inputs.

<!-- guides:end -->
