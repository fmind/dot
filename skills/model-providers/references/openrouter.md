---
name: openrouter
description: "OpenRouter model routing, API key authentication, and OpenAI-compatible requests."
---

# OpenRouter

Use OpenRouter when requested. The OpenAI-compatible base URL is `https://openrouter.ai/api/v1`; authenticate with `Authorization: Bearer` using `OPENROUTER_API_KEY` from the environment. OpenCode's explicit workstation default is OpenRouter.

1. OpenCode uses its native credential store. For other applications, supply `OPENROUTER_API_KEY` through a secret manager or an explicitly provisioned `dot secret run OPENROUTER_API_KEY -- COMMAND` scoped file; it is not exported globally. Never put it in a model configuration, command argument, diagnostic output, or skill example.
1. Read `GET /api/v1/models` to verify the exact `vendor/model` ID and supported parameters. OpenCode prefixes its provider: `openrouter/google/gemini-3.8-flash`; direct OpenRouter requests use `google/gemini-3.8-flash`. Do not use the OpenCode prefix in an API payload.
1. Use `GET /api/v1/key` as a read-only authenticated check, capturing the key and response privately and reporting only success/failure. This verifies the credential, not paid model access. For authorized inference use `/chat/completions`, bound output with `max_tokens`, and set a request timeout.
1. Use the existing application SDK; the OpenAI-compatible client accepts `base_url` and `api_key`. Verify support for tools, reasoning, streaming, and structured output against the selected model. Keep native provider routing unless endpoint control is requested; use `provider.require_parameters` when silent loss of a required parameter would break the application.
1. Distinguish invalid credentials, insufficient credit, rate limits, and provider/model errors. Honor `Retry-After` and bound retries. Do not switch to a different model, account, or provider automatically to evade a failure.

OpenCode configuration belongs to [agent-harnesses](../../agent-harnesses/references/opencode/GUIDE.md). Use `/connect` for the personal native login. For a customer project, set `provider.openrouter.options.apiKey` to an explicit environment/file reference or use a separate `XDG_DATA_HOME`; see [credential precedence](../../dot-cli/references/authentication.md#customer-overrides-and-isolation). Configure `model` and `small_model` explicitly to avoid auxiliary calls through a different provider. Shared skill discovery, compaction, permissions, and built-in agents need no OpenRouter plugin.

## Primary sources

- [Authentication](https://openrouter.ai/docs/api_reference/authentication), [API reference](https://openrouter.ai/docs/api/reference/overview), and [model catalog](https://openrouter.ai/models).
- [Provider routing](https://openrouter.ai/docs/features/provider-routing) and [announcements](https://openrouter.ai/announcements).
