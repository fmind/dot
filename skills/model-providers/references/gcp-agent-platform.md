---
name: gcp-agent-platform
description: "GCP Agent Platform model access with ADC and global location."
---

# GCP Agent Platform

Use GCP Agent Platform (Gemini Enterprise Agent Platform) by default for new model integrations. Prefer ADC, an explicit project, and `global` location. Product names changed; existing API hosts, IAM roles, and some SDK/provider identifiers still contain `aiplatform` or `vertex`.

1. **Require an explicit project, then apply defaults**: resolve the project from explicit application configuration, environment, or the user; ask when none is set rather than assuming a default billing project. Use `global`, the latest GA model of the [chosen tier](../SKILL.md#workflow) from the [model catalog](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models), and `ThinkingConfig(thinking_level="HIGH")` unless explicitly overridden. The REST setting is `generationConfig.thinkingConfig.thinkingLevel: "HIGH"`; `high` is a generation setting, not a model-ID suffix. Gemini 3.8 Flash and 4 Argon accept `LOW`, `MEDIUM` (their default), and `HIGH`; `MINIMAL` fails validation, and Argon also rejects `thinking_budget` with HTTP 400.
1. **Reuse existing ADC**: if authentication setup is requested, use `dot login gcp`, which keeps the configured ADC scopes that a bare `gcloud auth application-default login` drops; ordinary `gcloud auth login` alone does not establish ADC. Never run `agents-cli login`: it runs `gcloud auth login --update-adc` and switches the active account ([agents-cli](../../agent-frameworks/references/agents-cli/GUIDE.md#gotchas)). For deployed workloads, prefer the attached service account or approved impersonation. Delegate IAM/API enablement to [gcloud](../../gcloud/SKILL.md).
1. **Call Gemini through `google-genai`**: current SDKs expose `genai.Client(enterprise=True, project=project, location="global")` and `GOOGLE_GENAI_USE_ENTERPRISE=true`. Versions before 1.74.0 use `vertexai=True` and `GOOGLE_GENAI_USE_VERTEXAI=true` (still accepted later): check the locked version before selecting the spelling, and keep one backend selector. google-genai 3.0 keeps `v1beta1` for enterprise clients but makes `httpx2` the HTTP client and no longer installs `httpx`: `HttpOptions` client objects and caught transport exceptions must come from `httpx2`. Pass the project and location explicitly; do not rely on a bare `Client()` when API keys are also exported.
1. **Check the model's global availability**: the global REST host is `https://aiplatform.googleapis.com`, with paths under `/v1/projects/{project}/locations/global/publishers/google/models/{model}`. Global routing does not guarantee regional data residency; honor any project location requirement.
1. **Never print access tokens**: for verification, refresh ADC with token output captured in memory and discarded; never print access tokens. Confirm model access separately. Classify authentication, API enablement, IAM, model availability, and quota errors before proposing a change.

For OpenCode integrations explicitly requesting this provider, its provider identifier remains `google-vertex`; configure `options.project` and `options.location: "global"`.

## Explicit key fallback

This workstation stores no personal GCP Agent Platform key; use ADC. When an integration explicitly requires a key and ADC cannot be used, report that limitation and use a key supplied for that project, restricted to `aiplatform.googleapis.com`, from its secret manager or `dot secret run`. Read it explicitly and pass it to the selected client, or use the `x-goog-api-key` REST header. Never export it as `GOOGLE_API_KEY` or `GEMINI_API_KEY`, put it in a URL, or combine it with ADC in one request. google-genai 2.15.0 and later accept a key with project and location in enterprise mode; older versions treat keys as express-mode-only.

## Primary sources

- [Agent Platform quickstart](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/start) and [product name changes](https://docs.cloud.google.com/gemini-enterprise-agent-platform/vertex-ai-name-changes).
- [Google Gen AI SDK](https://googleapis.github.io/python-genai/) and [SDK releases](https://github.com/googleapis/python-genai/releases).
- [Locations and global endpoint](https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/locations).
- [Gemini models](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models) and [release notes](https://docs.cloud.google.com/gemini-enterprise-agent-platform/release-notes).
