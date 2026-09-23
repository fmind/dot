---
name: gcp-agent-platform
description: "GCP Agent Platform model access with ADC and global location."
---

# GCP Agent Platform

Use GCP Agent Platform (Gemini Enterprise Agent Platform) by default for new model integrations. Prefer ADC, an explicit project, and `global` location. Product names changed; existing API hosts, IAM roles, and some SDK/provider identifiers still contain `aiplatform` or `vertex`.

1. Resolve the project from explicit application/customer configuration first. For personal integrations only, default to `ai-studio-fmind`; ask for customer projects rather than charging the personal project. Use `global`, model `gemini-3.8-flash`, and `ThinkingConfig(thinking_level="HIGH")` unless explicitly overridden. The REST setting is `generationConfig.thinkingConfig.thinkingLevel: "HIGH"`; `high` is a generation setting, not a model-ID suffix.
1. Reuse existing ADC. If authentication setup is requested, use `gcloud auth application-default login`; ordinary `gcloud auth login` alone does not establish ADC. For deployed workloads, prefer the attached service account or approved impersonation. Delegate IAM/API enablement to [gcloud](../../gcloud/SKILL.md).
1. Use `google-genai` for Gemini model calls. Current SDKs expose `genai.Client(enterprise=True, project=project, location="global")` and `GOOGLE_GENAI_USE_ENTERPRISE=true`. Older versions use `vertexai=True` and `GOOGLE_GENAI_USE_VERTEXAI=true`: inspect the installed signature before selecting the spelling, and keep one backend selector. Pass the project and location explicitly; do not rely on a bare `Client()` when API keys are also exported.
1. Check the requested model's global availability. The global REST host is `https://aiplatform.googleapis.com`, with paths under `/v1/projects/{project}/locations/global/publishers/google/models/{model}`. Global routing does not guarantee regional data residency; honor any project location requirement.
1. For verification, refresh ADC with token output captured in memory and discarded; never print access tokens. Confirm model access separately. Classify authentication, API enablement, IAM, model availability, and quota errors before proposing a change.

For OpenCode integrations explicitly requesting this provider, its provider identifier remains `google-vertex`; configure `options.project` and `options.location: "global"`. The workstation's default OpenCode provider is explicitly OpenRouter.

## Explicit key fallback

The personal GCP Agent Platform authorization key is encrypted in chezmoi and deployed owner-only to `~/.config/dot/secrets/VERTEX_API_KEY`. It is restricted to `aiplatform.googleapis.com`; it is not an AI Studio credential. Use `dot secret run VERTEX_API_KEY -- uv run app.py` only when key access is authorized or ADC cannot be used and that limitation has been reported. Read `VERTEX_API_KEY` explicitly and pass it to the selected GCP Agent Platform client, or use the `x-goog-api-key` REST header. Never export it as `GOOGLE_API_KEY` or `GEMINI_API_KEY`, put it in a URL, or combine it with ADC in one request. Ordinary SDK calls must continue to use ADC. Check installed SDK support before combining key authentication with project/location arguments; some versions treat keys as express-mode-only.

## Personal billing

The personal project allowance is **US$100 per calendar month before credits**, across all services. Its billing account uses EUR, so the project alert budget is **EUR87** (rounded down from USD100 / 1.1463, ECB rate dated 2026-09-22). Recheck the conversion when changing the budget; it is not an automatic USD cap. Exclude all credits, including Ultra promotions, from budget spend; credits must not create an additional USD100 spending allowance. Actual-spend alerts should cover 50%, 80%, 90%, and 100%, with a 100% forecast alert and project-owner notifications.

Alert budgets do not stop usage. Cloud Billing's spend-cap preview supports GCP Agent Platform but currently requires console setup; even a configured cap can overshoot because of reporting latency. Do not claim a hard cap or redeemed Ultra credits without live evidence. Check the linked billing account's Credits page and the Developer Program benefits redemption separately.

## Primary sources

- [Agent Platform quickstart](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/start) and [product name changes](https://docs.cloud.google.com/gemini-enterprise-agent-platform/vertex-ai-name-changes).
- [Google Gen AI SDK](https://googleapis.github.io/python-genai/) and [SDK releases](https://github.com/googleapis/python-genai/releases).
- [Locations and global endpoint](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/locations).
- [Gemini 3.8 Flash](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash), [budget alerts](https://docs.cloud.google.com/billing/docs/how-to/budgets), and [spend caps](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps).
