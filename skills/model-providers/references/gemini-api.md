---
name: gemini-api
description: "Gemini Developer API access with an explicitly requested API key backend."
---

# Gemini API

Use the Gemini Developer API only when requested. It uses an AI Studio API key and its own endpoint, quotas, and model availability; GCP ADC is not this authentication path.

1. Read `GEMINI_API_KEY` from the environment. On this workstation its source is encrypted `secrets.fish`. Google SDK auto-discovery gives `GOOGLE_API_KEY` precedence when both variables exist; pass the intended key explicitly to avoid selecting an unrelated credential.
1. Inspect the installed `google-genai` client signature. Set `enterprise=False` (older SDKs: `vertexai=False`) and `api_key=os.environ["GEMINI_API_KEY"]` explicitly so ambient GCP backend flags cannot redirect the client. Keep backend selection scoped to the application instead of changing the whole shell.
1. Discover available models before choosing the model ID. REST uses `https://generativelanguage.googleapis.com` with the `x-goog-api-key` header; avoid keys in query strings or logged request objects. Listing models is a read-only access check, not inference proof.
1. For tool calling or structured output, use the selected model's documented features and validate returned arguments before executing tools. Keep retries bounded; distinguish an invalid/restricted key, unsupported model, and quota exhaustion.

Current Gemini API documentation describes migration from standard keys to authorization keys. Check the account's key type and current requirements when authentication fails; do not replace or broaden a key merely to test access.

## Primary sources

- [API keys and precedence](https://ai.google.dev/gemini-api/docs/api-key) and [model listing](https://ai.google.dev/api/models).
- [Google Gen AI SDK](https://googleapis.github.io/python-genai/) and [Gemini API release notes](https://ai.google.dev/gemini-api/docs/changelog).
