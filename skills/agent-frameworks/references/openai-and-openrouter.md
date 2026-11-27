---
name: openai-and-openrouter
description: "Call OpenAI Responses API or route multi-vendor models via OpenRouter with scoped keys."
---

# OpenAI SDK & OpenRouter

Use `openai` (`AsyncOpenAI`, `3.51.0+`) for OpenAI API integrations, or point `AsyncOpenAI` at OpenRouter (`https://openrouter.ai/api/v1`) when routing across open and proprietary vendors. Keep credentials strictly distinct: use `OPENAI_API_KEY` (or Workload Identity) for OpenAI and `OPENROUTER_API_KEY` for OpenRouter—never overload `OPENAI_API_KEY` for OpenRouter or export either globally.

## OpenAI Responses API

1. **Authenticate safely**: prefer `AsyncOpenAI(..., workload_identity=...)` where federated OIDC applies, or inject a scoped `OPENAI_API_KEY` per process via `with-secret` / secret manager; configure explicit timeouts and retries (`http_client=httpx2.AsyncClient(...)` or SDK defaults).
1. **Default to `client.responses`**: prefer `await client.responses.parse(...)` over legacy `chat.completions` for structured outputs and reasoning models:
   ```python
   response = await client.responses.parse(
       model="<verified-model-id>",
       instructions=SYSTEM_PROMPT,
       input=user_input,
       text_format=MyModel,
       reasoning={"effort": "high"},
       store=False,
   )
   parsed = response.output_parsed
   ```
1. **Zero-retention & strict tools**: default `store=False` unless server-side response state is explicitly authorized, mark function tools `strict: true` (`additionalProperties: false` via Pydantic schemas), bound `max_output_tokens` and `max_tool_calls`, and fail closed when `output_parsed is None` (refusal or truncation).

## OpenRouter (Opt-In Multi-Vendor Routing)

1. **Scope `OPENROUTER_API_KEY` per process**: load from a secret manager into `Authorization: Bearer $OPENROUTER_API_KEY` (never global env, config literals, CLI args, logs, or examples; `with-secret` manages only read-only `OPENROUTER_MANAGEMENT_KEY`).
1. **Query targeted model metadata**: inspect `GET /api/v1/model/<vendor>/<model>` (or `/models/<vendor>/<model>/endpoints`) for `supported_parameters` instead of the ~800 KB `/api/v1/models` dump. Pass direct slugs (`google/gemini-4-hydrogen`, not `openrouter/google/gemini-4-hydrogen`).
1. **Probe read-only & configure client**: verify auth privately via `GET /api/v1/key` (checks key, not paid model access); pass explicit `base_url="https://openrouter.ai/api/v1"` and `api_key=openrouter_key` to `AsyncOpenAI`, bound `/chat/completions` with `max_tokens` + timeout, and set `provider.require_parameters` when parameter drops would break callers.
1. **Batch offline workloads**: `POST /api/v1/batches` ([Batch API](https://openrouter.ai/docs/batch-quickstart): normal model slug, 24h window, ~1m `GET /api/v1/batches/{id}` polling, `custom_id` matching) routes to the cheapest batch provider, reserves estimated credits upfront, and rejects unsupported models.
1. **Classify failures without auto-switching**: separate bad keys, empty credit, rate limits (`Retry-After`), and upstream errors; never auto-switch models, accounts, or providers. Isolate customer keys per [customer isolation](../../dot-cli/references/authentication.md#customer-overrides-and-isolation).

## Primary sources

- [OpenAI Python SDK](https://github.com/openai/openai-python) · [Responses API](https://developers.openai.com/api/reference/resources/responses) · [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenRouter auth](https://openrouter.ai/docs/api_reference/authentication) · [API reference](https://openrouter.ai/docs/api_reference/overview) · [models](https://openrouter.ai/models) · [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection)
