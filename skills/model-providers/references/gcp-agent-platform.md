---
name: gcp-agent-platform
description: "GCP Agent Platform model access with ADC and global location."
---

# GCP Agent Platform

Use GCP Agent Platform (Gemini Enterprise Agent Platform) by default for new model integrations. Prefer ADC, an explicit project, and `global` location. Product names changed; existing API hosts, IAM roles, and some SDK/provider identifiers still contain `aiplatform` or `vertex`.

1. **Prefer the explicit project, then defaults**: resolve the project from explicit application/customer configuration first. For personal integrations only, default to `ai-studio-fmind`; ask for customer projects rather than charging the personal project. Use `global`, the latest GA model of the [chosen tier](../SKILL.md#workflow) from the [model catalog](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models), and `ThinkingConfig(thinking_level="HIGH")` unless explicitly overridden. The REST setting is `generationConfig.thinkingConfig.thinkingLevel: "HIGH"`; `high` is a generation setting, not a model-ID suffix. Gemini 3.8 Flash and 4 Argon accept `LOW`, `MEDIUM` (their default), and `HIGH`; `MINIMAL` fails validation, and Argon also rejects `thinking_budget` with HTTP 400.
1. **Reuse existing ADC**: if authentication setup is requested, use `dot login gcp`, which keeps the configured ADC scopes that a bare `gcloud auth application-default login` drops; ordinary `gcloud auth login` alone does not establish ADC. For deployed workloads, prefer the attached service account or approved impersonation. Delegate IAM/API enablement to [gcloud](../../gcloud/SKILL.md).
1. **Call Gemini through `google-genai`**: current SDKs expose `genai.Client(enterprise=True, project=project, location="global")` and `GOOGLE_GENAI_USE_ENTERPRISE=true`. Versions before 1.74.0 use `vertexai=True` and `GOOGLE_GENAI_USE_VERTEXAI=true` (still accepted later): check the locked version before selecting the spelling, and keep one backend selector. Pass the project and location explicitly; do not rely on a bare `Client()` when API keys are also exported.
1. **Check the model's global availability**: the global REST host is `https://aiplatform.googleapis.com`, with paths under `/v1/projects/{project}/locations/global/publishers/google/models/{model}`. Global routing does not guarantee regional data residency; honor any project location requirement.
1. **Never print access tokens**: for verification, refresh ADC with token output captured in memory and discarded; never print access tokens. Confirm model access separately. Classify authentication, API enablement, IAM, model availability, and quota errors before proposing a change.

For OpenCode integrations explicitly requesting this provider, its provider identifier remains `google-vertex`; configure `options.project` and `options.location: "global"`.

## Explicit key fallback

This workstation stores no personal GCP Agent Platform key; use ADC. When an integration explicitly requires a key and ADC cannot be used, report that limitation and use a key supplied for that project, restricted to `aiplatform.googleapis.com`, from its secret manager or `dot secret run`. Read it explicitly and pass it to the selected client, or use the `x-goog-api-key` REST header. Never export it as `GOOGLE_API_KEY` or `GEMINI_API_KEY`, put it in a URL, or combine it with ADC in one request. google-genai 2.15.0 and later accept a key with project and location in enterprise mode; older versions treat keys as express-mode-only.

## Personal billing

The personal project has a fixed monthly USD allowance before credits, across all services; the owner holds the amount privately, so ask for it before creating or changing a budget. The billing account uses EUR, so convert the allowance at a dated ECB rate, round down, and recheck the conversion when changing the budget; an alert budget is not an automatic USD cap. Exclude all credits, including Ultra promotions, from budget spend; credits must not create additional spending allowance. Actual-spend alerts should cover 50%, 80%, 90%, and 100%, with a 100% forecast alert and project-owner notifications.

Alert budgets do not stop usage. Cloud Billing's spend-cap preview supports GCP Agent Platform but currently requires console setup; even a configured cap can overshoot because of reporting latency. Do not claim a hard cap or redeemed Ultra credits without live evidence. Check the linked billing account's Credits page and the Developer Program benefits redemption separately.

## Primary sources

- [Agent Platform quickstart](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/start) and [product name changes](https://docs.cloud.google.com/gemini-enterprise-agent-platform/vertex-ai-name-changes).
- [Google Gen AI SDK](https://googleapis.github.io/python-genai/) and [SDK releases](https://github.com/googleapis/python-genai/releases).
- [Locations and global endpoint](https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/locations).
- [Gemini models](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models), [release notes](https://docs.cloud.google.com/gemini-enterprise-agent-platform/release-notes), [budget alerts](https://docs.cloud.google.com/billing/docs/how-to/budgets), and [spend caps](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps).
