---
name: model-providers
description: "Choose models and configure access via GCP Agent Platform, Gemini API, or OpenRouter."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/model-providers
  created: "2026-09-16"
  updated: "2026-11-12"
---

# Model Providers

Configure provider auth, endpoints, and model selection. Default new integrations to **GCP Agent Platform with ADC**, an explicit GCP project, `global`, the tier's latest GA model, and high thinking (preserving OpenCode's OpenRouter default). Use API keys only on explicit request or after reporting why ADC cannot work—never auto-fallback to keys or AI Studio on error.

## Workflow

1. **Choose the provider before checking credentials**: ambient keys never dictate the provider. Read only the matching guide; [gcloud](../gcloud/SKILL.md) owns IAM and [agent-harnesses](../agent-harnesses/SKILL.md) owns host configs.
1. **Pick tier, then verify exact GA ID**: default to **Gemini 4 Hydrogen** (`gemini-4-hydrogen`, GA 2026-11-12) for coding, agents, tool calls, and everyday execution (keep `gemini-3.8-flash` for half-price high-volume extraction); escalate to frontier (`Gemini 4 Argon` or `Carbon`; Argon GA 2026-10-13, Carbon GA 2026-11-10) for hard reasoning, architecture, or deep analysis. Look up exact IDs from the live provider catalog, never memory.
1. **Pin backend and scope secrets**: set the backend explicitly so ambient Google keys or env vars cannot hijack routing; inject keys per process via secret manager, native store, or `dot secret run NAME -- COMMAND`, never in code or config files.
1. **Probe read-only and fail closed**: separate auth, model access, and bounded/timed inference checks; never silently switch providers or billing projects on failure.

## Request contracts

Steer current models via instructions, thinking/effort levels, and native structured output:

- **Omit sampling parameters and prefill**: Gemini 3.6+ and Gemini 4 ignore `temperature`/`top_p`/`top_k` (deprecation headers now; future HTTP 400) and reject prefilled trailing `model` turns with 400; Claude returns 400 on assistant prefill and sampling parameters (all models from Anthropic API `2026-10-21`).
- **Never force Claude tool calls**: Claude Opus 5.5, Sonnet 5.5, and Fable 5.1+ return 400 on `tool_choice` `any` or `tool`—use `auto` with `strict: true` tools, or structured output for JSON.
- **Keep prefixes byte-stable and append-only**: static system text + tools first, dynamic context (date, retrieval, memory) in later turns; mutating prior turns breaks caching and invalidates thinking blocks on Claude Opus 5.5, Sonnet 5.5, and Fable 5.1+ (HTTP 400 on accounts created since 2026-08-31).

## Task guides

<!-- guides:start -->

- [gcp-agent-platform](references/gcp-agent-platform.md): GCP Agent Platform model access with ADC and global location.
- [gemini-api](references/gemini-api.md): Gemini Developer API access with an explicit API key backend.
- [openrouter](references/openrouter.md): OpenRouter model routing, API key authentication, and OpenAI-compatible requests.

<!-- guides:end -->
