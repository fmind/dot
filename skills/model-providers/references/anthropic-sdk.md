---
name: anthropic-sdk
description: "Configure async Anthropic SDK calls with Vertex or API auth, prefix caching, strict tools, and parsed outputs."
---

# Anthropic Python SDK (`2.9.0+`)

Use `anthropic` directly when integrating Claude models via Vertex AI (`anthropic[vertex]`, `AsyncAnthropicVertex`) or Anthropic API (`AsyncAnthropic`); follow [model-providers](../SKILL.md#request-contracts) for cross-provider rules.

## Workflow

1. **Choose auth & async client**: prefer GCP Vertex ADC (`AsyncAnthropicVertex(project_id=project, region="global")`) on GCP workloads, or inject `ANTHROPIC_API_KEY` via `with-secret` / secret store for direct Anthropic API calls (`AsyncAnthropic(timeout=60.0, max_retries=2)` using built-in `httpx2`).
1. **Parse typed outputs natively**: pass `output_format=MyModel` on `await client.messages.parse(...)` and read `message.parsed_output` rather than parsing raw JSON strings manually.
1. **Respect Claude 5.x constraints**: omit sampling params (`temperature`, `top_p`, `top_k`) and trailing assistant prefills; keep `tool_choice={"type": "auto"}` with `strict: true` schemas on Opus 5.5, Sonnet 5.5, and Fable 5.1+ (HTTP 400 on `any` or named tool forcing); enable `thinking=...` cleanly and keep conversation turns append-only (mutating prior turns invalidates thinking blocks and cache prefixes).
1. **Enable prompt caching & OTel safely**: mark static system prompts and tool definitions with `cache_control: {"type": "ephemeral"}` at prefix boundaries, and record `gen_ai.*` latency/usage spans without logging secret tokens or unapproved bodies.

## Documentation

- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) · [Claude on Vertex AI](https://platform.claude.com/docs/en/build-with-claude/claude-on-vertex-ai) · [Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
