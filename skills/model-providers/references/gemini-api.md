---
name: gemini-api
description: "Gemini Developer API access with an explicit API key backend."
---

# Gemini API

Use the Gemini Developer API (AI Studio key, separate endpoint/quotas from GCP ADC) only when explicitly requested; no personal Gemini/Google key is stored on this workstation.

1. **Scope the supplied key**: inject an authorized Developer API key per process via an app-specific env var or secret store—never export global `GEMINI_API_KEY` or `GOOGLE_API_KEY`, and check standard-vs-authorization key rules on auth failures without broadening key scope.
1. **Pin the backend**: pass `enterprise=False` (`<1.74.0`: `vertexai=False`) and the explicit `api_key` to `google-genai` so ambient env vars cannot redirect requests.
1. **Resolve exact `v1` model IDs**: REST uses `https://generativelanguage.googleapis.com` with `x-goog-api-key` (never query strings or logged objects; model listing checks auth, not inference). `google-genai` 3.0+ defaults to `v1`, which omits `-latest` aliases like `gemini-flash-latest`—pin exact versions or pass `HttpOptions(api_version="v1beta")` when required.
1. **Disable request logging for customer data**: new paid-tier projects log `generateContent`, `streamGenerateContent`, and `batchGenerateContent` payloads by default since 2026-10-26—set `GenerateContentConfig(store=False)` (Developer API only) or disable Generate Content API logging in Logs and Datasets.

## Primary sources

- [API keys and precedence](https://ai.google.dev/gemini-api/docs/api-key) · [model listing](https://ai.google.dev/api/models) · [Google Gen AI SDK](https://googleapis.github.io/python-genai/) · [changelog](https://ai.google.dev/gemini-api/docs/changelog)
