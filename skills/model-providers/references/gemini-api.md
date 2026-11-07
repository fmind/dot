---
name: gemini-api
description: "Gemini Developer API access with an explicitly requested API key backend."
---

# Gemini API

Use the Gemini Developer API only when requested. It uses an AI Studio API key and its own endpoint, quotas, and model availability; GCP ADC is not this authentication path.

1. **Use only an explicitly supplied key**: obtain an explicitly supplied Developer API credential for the authorized integration. This workstation stores no personal Gemini or Google API key. Keep Developer API credentials in a process-scoped, application-specific variable or secret store, not globally exported as `GEMINI_API_KEY` or `GOOGLE_API_KEY`.
1. **Select the backend explicitly**: inspect the installed `google-genai` client signature. Set `enterprise=False` (older SDKs: `vertexai=False`) and pass the intended key explicitly so ambient Google keys or backend flags cannot redirect the client. Keep backend selection scoped to the application instead of changing the whole shell.
1. **Discover models before choosing an ID**: REST uses `https://generativelanguage.googleapis.com` with the `x-goog-api-key` header; avoid keys in query strings or logged request objects. Listing models is a read-only access check, not inference proof. google-genai 3.0+ calls the Developer API on `v1` instead of `v1beta`, where `-latest` aliases such as `gemini-flash-latest` do not exist; pin a model version, or set `HttpOptions(api_version="v1beta")` for a v1beta-only feature.
1. **Keep customer data out of request storage**: since 2026-10-26, new paid-tier projects store `generateContent`, `streamGenerateContent`, and `batchGenerateContent` requests by default. For customer data, pass `GenerateContentConfig(store=False)` on each request or turn off Generate Content API logging in the Logs and Datasets settings; Agent Platform does not support this field.

Current Gemini API documentation describes migration from standard keys to authorization keys. Check the account's key type and current requirements when authentication fails; do not replace or broaden a key merely to test access.

## Primary sources

- [API keys and precedence](https://ai.google.dev/gemini-api/docs/api-key) and [model listing](https://ai.google.dev/api/models).
- [Google Gen AI SDK](https://googleapis.github.io/python-genai/) and [Gemini API release notes](https://ai.google.dev/gemini-api/docs/changelog).
