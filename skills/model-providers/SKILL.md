---
name: model-providers
description: "Choose models and configure access via GCP Agent Platform, Gemini, Anthropic/Claude, OpenAI, OpenRouter, or LangExtract."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/model-providers
  created: "2026-09-16"
  updated: "2026-11-17"
---

# Model Providers

Configure provider auth, endpoints, and model selection. Default new integrations to **GCP Agent Platform with ADC**, an explicit GCP project, `global`, the tier's latest GA model, and high thinking (preserving OpenCode's OpenRouter default). Use API keys only on explicit request or after reporting why ADC cannot work—never auto-fallback to keys or AI Studio on error.

## Workflow

1. **Choose the provider before checking credentials**: ambient keys never dictate the provider. Load the matching provider guide(s); [gcloud](../gcloud/SKILL.md) owns IAM and [agent-harnesses](../agent-harnesses/SKILL.md) owns host configs.
1. **Pick tier, then verify exact GA ID**: default to **Gemini 4 Hydrogen** (`gemini-4-hydrogen`, GA 2026-11-12) for coding, agents, tool calls, and everyday execution (keep `gemini-3.8-flash` for half-price high-volume extraction); escalate to frontier (`Gemini 4 Argon` or `Carbon`; Argon GA 2026-10-13, Carbon GA 2026-11-10) for hard reasoning, architecture, or deep analysis. Look up exact IDs from the live provider catalog, never memory.
1. **Pin backend and scope secrets**: set the backend explicitly so ambient Google keys or env vars cannot hijack routing; inject keys per process via secret manager, native store, or `with-secret NAME -- COMMAND`, never in code or config files.
1. **Probe read-only and fail closed**: separate auth, model access, and bounded/timed inference checks; never silently switch providers or billing projects on failure.

## Request contracts

Steer current models via instructions, thinking/effort levels, and native structured output:

- **Omit sampling parameters and prefill**: Gemini 3.6+ / 4 and Claude (`2026-10-21+`) reject prefilled assistant turns with HTTP 400 and deprecate or reject `temperature`/`top_p`/`top_k`.
- **Never force Claude tool calls**: Claude 5.x returns 400 on `tool_choice` `any` or `tool`—use `auto` with `strict: true` tools, or structured output ([anthropic-sdk](references/anthropic-sdk.md)).
- **Keep prefixes byte-stable and append-only**: static system text + tools first, dynamic context in later turns; mutating prior turns breaks caching and invalidates Claude 5.x thinking blocks (HTTP 400).

## Task guides

<!-- guides:start -->

- [anthropic-sdk](references/anthropic-sdk.md): Configure async Anthropic SDK calls with Vertex or API auth, prefix caching, strict tools, and parsed outputs.
- [gcp-agent-platform](references/gcp-agent-platform.md): GCP Agent Platform model access with ADC and global location.
- [gemini-api](references/gemini-api.md): Gemini Developer API access with an explicit API key backend.
- [langextract](references/langextract.md): Extract structured facts from text with LangExtract and source-grounded evidence.
- [openai-sdk](references/openai-sdk.md): Configure async OpenAI Responses API calls, Workload Identity, strict Pydantic outputs, and reasoning effort.
- [openrouter](references/openrouter.md): OpenRouter model routing, API key authentication, and OpenAI-compatible requests.

<!-- guides:end -->

## Documentation

- [GCP Agent Platform models](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models) · [Google Gen AI SDK](https://googleapis.github.io/python-genai/) · [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python) · [OpenAI SDK](https://github.com/openai/openai-python) · [OpenRouter](https://openrouter.ai/docs/quickstart) · [LangExtract](https://github.com/google/langextract)
- Releases: [Agent Platform release notes](https://docs.cloud.google.com/gemini-enterprise-agent-platform/release-notes) · [python-genai](https://github.com/googleapis/python-genai/releases)
- Companions: [agent-frameworks](../agent-frameworks/SKILL.md), [gcloud](../gcloud/SKILL.md), [dot-cli](../dot-cli/SKILL.md).
