---
name: gcp-agent-platform
description: "GCP Agent Platform model access with ADC and global location."
---

# GCP Agent Platform

Default new integrations to GCP Agent Platform (Gemini Enterprise Agent Platform) with ADC, an explicit project, and `global` (hosts, IAM roles, and SDK IDs still use `aiplatform` or `vertex`).

1. **Require an explicit project and thinking config**: ask if no project is configured rather than billing a default. Use `global`, the [tier's](../SKILL.md#workflow) latest GA ID from the [model catalog](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models), and `ThinkingConfig(thinking_level="HIGH")` (`generationConfig.thinkingConfig.thinkingLevel: "HIGH"`, never a model-ID suffix). `Gemini 4 Hydrogen` accepts `LOW`, `MEDIUM`, `HIGH` (default), and `XHIGH`, uses a unified 1,048,576 input+output token limit (`v1beta1` `continuation_token` long decodes beyond 65,536 foreground tokens), implicit durable caching ≥4,096 tokens only (explicit caching unsupported), and native Office (`.docx`/`.pptx`/`.xlsx`) plus OpenDocument inputs; `Gemini 4 Argon`/`Carbon` and `Gemini 3.8 Flash` accept `LOW`, `MEDIUM` (default), and `HIGH`. Across all four, `MINIMAL` fails validation and Gemini 4 returns HTTP 400 on `thinking_budget`.
1. **Authenticate via ADC**: set up local ADC with `dot login gcp` (preserves scopes dropped by bare `gcloud auth application-default login`; plain `gcloud auth login` sets no ADC, and `agents-cli login` overwrites ADC scopes and active account—see [agents-cli](../../agent-frameworks/references/agents-cli/GUIDE.md#gotchas)). Use attached service accounts or approved impersonation in deployments, and [gcloud](../../gcloud/SKILL.md) for IAM/APIs.
1. **Configure `google-genai` explicitly**: pass `genai.Client(enterprise=True, project=project, location="global")` / `GOOGLE_GENAI_USE_ENTERPRISE=true` (`<1.74.0` uses `vertexai=True` / `GOOGLE_GENAI_USE_VERTEXAI=true`; pick one). `google-genai` 3.0 keeps `v1beta1` on enterprise but switches from `httpx` to `httpx2` for `HttpOptions` clients and transport exceptions; never call bare `Client()` alongside exported API keys.
1. **Check endpoint and residency**: `global` routes via `https://aiplatform.googleapis.com` (`/v1/projects/{project}/locations/global/publishers/google/models/{model}`) without regional residency guarantees—use a regional location when residency requires it.
1. **Probe without leaking tokens**: refresh ADC in memory without printing tokens, and classify auth, API, IAM, model-access, and quota failures separately. OpenCode uses provider ID `google-vertex` (`options.project`, `options.location: "global"`).

## Explicit key fallback

No personal Agent Platform key exists here. If ADC is impossible and a key is explicitly requested, load a project-scoped `aiplatform.googleapis.com`-restricted key via secret manager or `dot secret run`, passing it to the client (`google-genai` 2.15.0+ supports enterprise keys with project/location; older versions restrict keys to express mode) or `x-goog-api-key`—never via `GOOGLE_API_KEY`, `GEMINI_API_KEY`, URLs, or mixed with ADC.

## Primary sources

- [Agent Platform quickstart](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/start) · [name changes](https://docs.cloud.google.com/gemini-enterprise-agent-platform/vertex-ai-name-changes) · [locations](https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/locations)
- [Google Gen AI SDK](https://googleapis.github.io/python-genai/) · [SDK releases](https://github.com/googleapis/python-genai/releases) · [models](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models) · [Gemini 4 Hydrogen](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/4-hydrogen) · [release notes](https://docs.cloud.google.com/gemini-enterprise-agent-platform/release-notes)
