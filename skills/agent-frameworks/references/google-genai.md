---
name: google-genai
description: "Call Gemini on GCP Agent Platform (ADC) or Gemini Developer API with google-genai."
---

# Google Gen AI (`google-genai`)

Default to **GCP Agent Platform with ADC**, explicit project, and `global` (hosts, IAM, and SDK IDs still use `aiplatform`/`vertex`). Use Gemini Developer API (AI Studio key) only on explicit request; no personal Google key is stored here. See [request contracts](request-contracts.md) for tiers, pricing, 1M window, `continuation_token`, implicit caching (`>= 4,096` tokens), and Office/ODF inputs.

## GCP Agent Platform (Default)

1. **Project, location, & thinking**: ask if unset. Use `global`, verified GA ID (`gemini-4-hydrogen` default, `gemini-4-neon` verified-enterprise step-up, `gemini-4-carbon`/`argon` frontier), and `ThinkingConfig(thinking_level="HIGH")` (never model-ID suffix).
1. **ADC auth**: run `dot login gcp` (preserves scopes dropped by bare `gcloud auth application-default login`; `agents-cli login` overwrites scopes—see [agents-cli](agents-cli/GUIDE.md#gotchas)). Use attached SAs or impersonation in deployments and [gcloud](../../gcloud/SKILL.md) for IAM/APIs.
1. **Explicit client (`3.6+`)**: pass `genai.Client(enterprise=True, project=project, location="global")` or `GOOGLE_GENAI_USE_ENTERPRISE=true` (`<1.74.0`: `vertexai=True`; `3.0+` keeps `v1beta1`, uses `httpx2` for `HttpOptions`, adds Interactions tool retrieval in `3.6.0+`). Never call bare `Client()` alongside exported API keys.
1. **Residency & probing**: `global` routes via `https://aiplatform.googleapis.com` without regional residency guarantees. Refresh ADC in memory without printing tokens; classify auth, API, IAM, model-access, and quota failures separately.
1. **Enterprise key fallback**: if ADC is impossible and requested, inject an `aiplatform.googleapis.com`-restricted key via secret manager/`with-secret` (`2.15.0+` supports enterprise keys with project/location) or `x-goog-api-key`—never `GOOGLE_API_KEY`, `GEMINI_API_KEY`, URLs, or mixed with ADC.

## Async Patterns

- **Structured output (`client.aio`)**: run inside an `asyncio` lifespan without wrapper frameworks:
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
- **Retries, batch, & OTel**: wrap 429/503/network errors with deadline-aware `stamina` (`26.2+`) per [api-client](../../python/references/api-client/GUIDE.md); keep static prefixes first for implicit caching (`>= 4,096` tokens); use `client.aio.batches.create(...)` for bulk jobs; emit `gen_ai.*` spans without prompt/completion bodies ([observability](../../python/references/observability.md)).

## Gemini Developer API (Opt-In)

Separate endpoint/quotas (`https://generativelanguage.googleapis.com`, `x-goog-api-key` header, never query strings/logs; model listing checks auth, not inference):

1. **Scope key & pin backend**: inject per process via app env var or secret store (never export global `GEMINI_API_KEY`/`GOOGLE_API_KEY`; check standard-vs-authorization key rules on auth errors), passing `enterprise=False` (`<1.74.0`: `vertexai=False`) and explicit `api_key`.
1. **Pin exact `v1` IDs**: `3.0+` defaults to `v1`, omitting `-latest` aliases (`gemini-flash-latest`)—pin exact versions or pass `HttpOptions(api_version="v1beta")`.
1. **Disable logging for customer data**: new paid-tier projects log generate/stream/batch payloads by default since 2026-10-26—set `GenerateContentConfig(store=False)` (Developer API only) or disable Generate Content API logging in Logs and Datasets.

## Primary sources

- [Agent Platform](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/start) · [models](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models) · [locations](https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/locations) · [name changes](https://docs.cloud.google.com/gemini-enterprise-agent-platform/vertex-ai-name-changes) · [release notes](https://docs.cloud.google.com/gemini-enterprise-agent-platform/release-notes)
- [Gen AI SDK](https://googleapis.github.io/python-genai/) · [releases](https://github.com/googleapis/python-genai/releases) · [AI Studio keys](https://aistudio.google.com/docs/api-key) · [changelog](https://aistudio.google.com/docs/changelog)
