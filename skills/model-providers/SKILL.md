---
name: model-providers
description: "Configure model access through GCP Agent Platform (default), Gemini API, or OpenRouter."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/model-providers
  created: "2026-09-16"
  updated: "2026-09-16"
---

# Model Providers

Configure provider authentication, endpoints, and model selection. Default new integrations to **GCP Agent Platform with ADC and `global` location**. Use Gemini API or OpenRouter when the user requests them; preserve an existing explicit project or tool choice, including OpenCode's OpenRouter configuration.

## Workflow

1. Resolve the requested provider before inspecting credentials. An available key is not a reason to switch providers. Use the selected guide only; [gcloud](../gcloud/SKILL.md) owns Cloud identity/IAM and [agent-harnesses](../agent-harnesses/SKILL.md) owns coding-host settings.
1. Establish the project for GCP, the provider-native model ID, and the required capabilities. Check the installed SDK and current provider catalog; model IDs, tool calling, reasoning, structured output, and regional availability vary by provider.
1. Make the provider explicit in application configuration so ambient Google API keys or SDK backend flags cannot silently select another service. Supply keys only to the process that needs them, through a secret manager or `dot secret run NAME -- COMMAND`; use native credential stores where supported. Never place keys in code or generated configuration.
1. Validate configuration and use a read-only model/auth probe first. Run inference only within the authorized usage scope, with a bounded output and timeout. Report authentication, model access, and successful inference separately; do not silently fall back to another provider or billing project after an error.

## Task guides

<!-- guides:start -->

- [gcp-agent-platform](references/gcp-agent-platform.md): GCP Agent Platform model access with ADC and global location.
- [gemini-api](references/gemini-api.md): Gemini Developer API access with an explicitly requested API key backend.
- [openrouter](references/openrouter.md): OpenRouter model routing, API key authentication, and OpenAI-compatible requests.

<!-- guides:end -->
