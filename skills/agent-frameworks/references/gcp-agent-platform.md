---
name: gcp-agent-platform
description: "GCP Agent Platform model access with ADC and global location."
---

# GCP Agent Platform

Default to GCP Agent Platform with ADC, an explicit project, and `global` (hosts, IAM roles, and SDK IDs still use `aiplatform` or `vertex`).

1. **Explicit project and thinking**: ask if no project is set. Use `global`, latest GA ID from [models](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models) (`gemini-4-hydrogen` default, `gemini-4-neon` verified-enterprise step-up without Deferred tier, `gemini-4-carbon`/`argon` frontier), and `ThinkingConfig(thinking_level="HIGH")` (never a model-ID suffix). See [request contracts](request-contracts.md) for thinking levels, unified 1M window, `v1beta1` `continuation_token`, implicit caching (`>= 4,096` tokens), and Office/ODF inputs.
1. **Authenticate via ADC**: run `dot login gcp` (preserves scopes dropped by bare `gcloud auth application-default login`; `agents-cli login` overwrites scopes—see [agents-cli](../../agent-frameworks/references/agents-cli/GUIDE.md#gotchas)). Use attached service accounts or impersonation in deployments, and [gcloud](../../gcloud/SKILL.md) for IAM/APIs.
1. **Configure `google-genai` explicitly**: pass `genai.Client(enterprise=True, project=project, location="global")` / `GOOGLE_GENAI_USE_ENTERPRISE=true` (`<1.74.0` uses `vertexai=True`). `3.0+` keeps `v1beta1`, uses `httpx2` for `HttpOptions`, and adds Interactions tool retrieval in `3.6.0+`; never call bare `Client()` alongside exported API keys.
1. **Check residency**: `global` routes via `https://aiplatform.googleapis.com` (`/v1/projects/{project}/locations/global/publishers/google/models/{model}`) without regional residency guarantees.
1. **Probe safely**: refresh ADC in memory without printing tokens; classify auth, API, IAM, model-access, and quota failures separately.

## Async `google-genai` (`3.6+`) Patterns

- **Async structured output (`aio`)**: use `client.aio` inside an `asyncio` lifespan without wrapper frameworks:
  ```python
  response = await client.aio.models.generate_content(
      model="gemini-4-hydrogen",
      contents=prompt,
      config=types.GenerateContentConfig(
          response_mime_type="application/json",
          response_schema=MyModel,
          thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
      ),
  )
  result = MyModel.model_validate_json(response.text)
  ```
- **Retries, batch, & telemetry**: wrap 429/503/network errors with deadline-aware `stamina` (`26.2+`) per [api-client](../../python/references/api-client/GUIDE.md); keep static instructions + schemas at prefix start for implicit caching (`>= 4,096` tokens); run bulk jobs via `await client.aio.batches.create(...)`; emit OTel `gen_ai.*` attributes without prompt/completion bodies ([observability](../../python/references/observability.md)).

## Explicit key fallback

No personal Agent Platform key exists here. If ADC is impossible and a key is explicitly requested, inject an `aiplatform.googleapis.com`-restricted key via secret manager or `with-secret` into the client (`google-genai` `2.15.0+` supports enterprise keys with project/location) or `x-goog-api-key`—never via `GOOGLE_API_KEY`, `GEMINI_API_KEY`, URLs, or mixed with ADC.

## Primary sources

- [Agent Platform quickstart](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/start) · [name changes](https://docs.cloud.google.com/gemini-enterprise-agent-platform/vertex-ai-name-changes) · [locations](https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/locations)
- [Google Gen AI SDK](https://googleapis.github.io/python-genai/) · [SDK releases](https://github.com/googleapis/python-genai/releases) · [models](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models) · [Gemini 4 Hydrogen](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/4-hydrogen) · [Gemini 4 Neon](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/4-neon) · [release notes](https://docs.cloud.google.com/gemini-enterprise-agent-platform/release-notes)
