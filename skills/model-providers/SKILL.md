---
name: model-providers
description: "Choose models and configure access via Vertex AI, Gemini API, or OpenRouter."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/model-providers
  created: "2026-09-16"
  updated: "2026-11-07"
---

# Model Providers

Configure provider authentication, endpoints, and model selection. Default new integrations to **GCP Agent Platform with ADC**, an explicit GCP project, `global`, the latest GA model of the chosen tier, and high thinking. Preserve OpenCode's OpenRouter default. Use API keys only when explicitly requested or as a last resort after reporting why ADC cannot work; never retry automatically with a key or switch to AI Studio after an error.

## Workflow

1. **Never let a key pick the provider**: resolve the requested provider before inspecting credentials. An available key is not a reason to switch providers. Use the selected guide only; [gcloud](../gcloud/SKILL.md) owns Cloud identity/IAM and [agent-harnesses](../agent-harnesses/SKILL.md) owns coding-host settings.
1. **Choose the tier, then the latest model**: default to the workhorse tier (the latest GA Flash) for agents, tool calls, extraction, and high-volume or latency-sensitive work. Escalate to the frontier tier (Gemini 4 Argon, GA and public since 2026-10-13) for complex long-horizon reasoning, coding, or analysis where quality outweighs cost and latency. Resolve the exact ID from the provider's current model list, never from memory, and confirm it with the read-only probe.
1. **Pin the provider and scope keys**: make the provider explicit in application configuration so ambient Google API keys or SDK backend flags cannot silently select another service. Supply keys only to the process that needs them, through a secret manager or `dot secret run NAME -- COMMAND`; use native credential stores where supported. Never place keys in code or generated configuration.
1. **Probe read-only; never silently fall back**: validate configuration and use a read-only model/auth probe first. Run inference only within the authorized usage scope, with a bounded output and timeout. Report authentication, model access, and successful inference separately; do not silently fall back to another provider or billing project after an error.

## Request contracts

Current models reject request habits from older ones; steer with instructions, thinking level or effort, and native structured output instead.

- **Send no sampling parameters or prefill**: Gemini 3.6+ and Gemini 4 ignore `temperature`, `top_p`, and `top_k` (deprecation headers now, HTTP 400 in a future release) and return 400 when the last turn is a prefilled `model` turn. Current Claude models return 400 on an assistant prefill and on sampling parameters (on every model from Anthropic API version `2026-10-21`).
- **Do not force a Claude tool call**: Claude Opus 5.5, Sonnet 5.5, and Fable 5.1 return 400 on `tool_choice` `any` or `tool`; use `auto` with `strict: true` tools, or structured output when the forced call only existed to get JSON.
- **Keep the prefix stable and append only**: keep system text and tool definitions byte-stable and append per-turn content (date, retrieval, changing memory) in later messages. Rebuilding the prefix breaks prompt caching, and on Claude Opus 5.5, Sonnet 5.5, and Fable 5.1 editing earlier turns invalidates their thinking blocks (HTTP 400 for accounts created since 2026-08-31).

## Task guides

<!-- guides:start -->

- [gcp-agent-platform](references/gcp-agent-platform.md): GCP Agent Platform model access with ADC and global location.
- [gemini-api](references/gemini-api.md): Gemini Developer API access with an explicitly requested API key backend.
- [openrouter](references/openrouter.md): OpenRouter model routing, API key authentication, and OpenAI-compatible requests.

<!-- guides:end -->
