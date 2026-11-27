---
name: agent-frameworks
description: "Build/eval Python AI agents & MCP servers: Gemini/Claude/OpenAI/OpenRouter, ADK, LangGraph, RAG, prompts, LangExtract, A2A, ACP."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-frameworks
  created: "2026-09-16"
  updated: "2026-11-25"
---

# Agent Frameworks & Model Providers

Default to **GCP Agent Platform with ADC**, explicit project, `global`, latest GA model + high thinking ([request-contracts](references/request-contracts.md)). Never auto-fallback to ambient keys; selecting a framework never authorizes provider calls, traces, or deploys.

## Workflow

1. **Pick the simplest tier**: **Direct SDK** ([google-genai](references/google-genai.md)) for single calls/chains; **Google ADK** (`google-adk>=2.14.1` on [python/bootstrap](../python/references/foundation/references/bootstrap.md) + [cloud-run](../gcloud/references/cloud-run/GUIDE.md), or opt-in `agents-cli`); or **LangGraph** + `langchain` for durable state or non-Google stacks.
1. **Install & configure safely**: add SDKs with `UV_MALWARE_CHECK=1 uv add --preview-features malware-check <pkg>`; inject keys per process via secret manager or `with-secret`, and use thinking/effort levels + native structured output ([request-contracts](references/request-contracts.md)).
1. **Verify**: load `system-prompts`, `evaluation`, and `rag-and-vectors` as needed; audit non-trivial agent/RAG designs with `fmind-review-agents` ([subagent](../subagent/SKILL.md)).

## Task guides

<!-- guides:start -->

- [a2a](references/a2a.md): A2A clients, servers, Agent Cards, task lifecycle, and official guidance.
- [acp](references/acp.md): ACP editor-agent sessions, capability negotiation, streaming, and permission handling.
- [agents-cli](references/agents-cli/GUIDE.md): Scaffold, test, eval, and deploy enterprise ADK agents with agents-cli.
- [anthropic-sdk](references/anthropic-sdk.md): Async Claude calls via Vertex ADC or API key, caching, and parsed outputs.
- [evaluation](references/evaluation/GUIDE.md): Evaluate prompts, retrieval, and agents with graded multi-trial runs.
- [google-adk](references/google-adk.md): Build Google ADK agents, workflows, tools, and sessions.
- [google-genai](references/google-genai.md): Call Gemini on GCP Agent Platform (ADC) or Gemini Developer API with google-genai.
- [langchain](references/langchain.md): Use LangChain create_agent, middleware, and MCP tools in LangGraph.
- [langextract](references/langextract.md): Source-grounded extraction with LangExtract and strict validation.
- [langgraph](references/langgraph.md): Build durable LangGraph workflows, checkpoints, streaming, and interrupts.
- [mcp](references/mcp/GUIDE.md): MCP tool and context clients/servers, transports, schemas, and protocol tests.
- [openai-and-openrouter](references/openai-and-openrouter.md): Call OpenAI Responses API or route multi-vendor models via OpenRouter with scoped keys.
- [rag-and-vectors](references/rag-and-vectors.md): Build pgvector/DuckDB hybrid RAG, tenant ACLs, and Gemini embeddings.
- [system-prompts](references/system-prompts.md): Design layered cache-friendly system prompts, guardrails, and schemas.

<!-- guides:end -->

## Documentation

- Companions: [python](../python/SKILL.md), [gcloud](../gcloud/SKILL.md), [finops](../finops/SKILL.md), [code-security](../code-security/SKILL.md), [dot-cli](../dot-cli/SKILL.md).
