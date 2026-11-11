---
name: openrouter
description: "OpenRouter model routing, API key authentication, and OpenAI-compatible requests."
---

# OpenRouter

Use OpenRouter (`https://openrouter.ai/api/v1`, `Authorization: Bearer $OPENROUTER_API_KEY`) when requested; it is OpenCode's workstation default.

1. **Scope `OPENROUTER_API_KEY` per process**: OpenCode uses its native store; other apps load it via secret manager or `dot secret run OPENROUTER_API_KEY -- COMMAND` (never global env, config literals, CLI args, logs, or examples).
1. **Query targeted model metadata**: inspect `GET /api/v1/model/<vendor>/<model>` (or `/models/<vendor>/<model>/endpoints`) for `supported_parameters` instead of the ~800 KB `/api/v1/models` dump. Strip OpenCode's `openrouter/` prefix in direct API calls (`google/gemini-3.8-flash`, not `openrouter/google/gemini-3.8-flash`).
1. **Probe read-only first**: check `GET /api/v1/key` privately without printing secrets (verifies key, not paid model access); bound `/chat/completions` with `max_tokens` and a timeout.
1. **Configure OpenAI-compatible SDKs**: pass `base_url` and `api_key`, verify tool/reasoning/streaming/schema support on the target model, and set `provider.require_parameters` when parameter drops would break callers.
1. **Batch offline workloads**: `POST /api/v1/batches` ([Batch API](https://openrouter.ai/docs/batch-quickstart): normal model slug, 24h window, ~1m `GET /api/v1/batches/{id}` polling, `custom_id` matching) routes to the cheapest batch provider, reserves estimated credits upfront, and rejects models without batch support.
1. **Classify failures without auto-switching**: separate bad keys, empty credit, rate limits (`Retry-After`), and upstream errors; never auto-switch models, accounts, or providers.

For OpenCode ([guide](../../agent-harnesses/references/opencode/GUIDE.md)), sign in personally via `opencode auth login` (or `/connect` in the TUI), isolate customer keys via `provider.openrouter.options.apiKey` env/file refs or `XDG_DATA_HOME` ([credential precedence](../../dot-cli/references/authentication.md#customer-overrides-and-isolation)), and pin both `model` and `small_model` (no OpenRouter plugin needed).

## Primary sources

- [Authentication](https://openrouter.ai/docs/api_reference/authentication) · [API reference](https://openrouter.ai/docs/api_reference/overview) · [models](https://openrouter.ai/models) · [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection) · [blog](https://openrouter.ai/blog)
