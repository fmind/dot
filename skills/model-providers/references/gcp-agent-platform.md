---
name: gcp-agent-platform
description: "GCP Agent Platform model access with ADC and global location."
---

# GCP Agent Platform

Use GCP Agent Platform (Gemini Enterprise Agent Platform, formerly Vertex AI) by default for new model integrations. Prefer ADC, an explicit project, and `global` location. Product names changed; existing API hosts, IAM roles, and some SDK/provider identifiers still contain `aiplatform` or `vertex`.

1. Resolve `GOOGLE_CLOUD_PROJECT` from the project's explicit configuration. If absent, ask for the intended project; do not silently choose a billing project. Set `GOOGLE_CLOUD_LOCATION=global` in that project's configuration unless the user requests a region and the model supports it.
1. Reuse existing ADC. If authentication setup is requested, use `gcloud auth application-default login`; ordinary `gcloud auth login` alone does not establish ADC. For deployed workloads, prefer the attached service account or approved impersonation. Delegate IAM/API enablement to [gcloud](../../gcloud/SKILL.md).
1. Use `google-genai` for Gemini model calls. Current SDKs expose `genai.Client(enterprise=True, project=project, location="global")` and `GOOGLE_GENAI_USE_ENTERPRISE=true`. Older versions use `vertexai=True` and `GOOGLE_GENAI_USE_VERTEXAI=true`: inspect the installed signature before selecting the spelling, and keep one backend selector. Pass the project and location explicitly; do not rely on a bare `Client()` when API keys are also exported.
1. Check the requested model's global availability. The global REST host is `https://aiplatform.googleapis.com`, with paths under `/v1/projects/{project}/locations/global/publishers/google/models/{model}`. Global routing does not guarantee regional data residency; honor any project location requirement.
1. For verification, refresh ADC with token output captured in memory and discarded; never print access tokens. Confirm model access separately. Classify authentication, API enablement, IAM, model availability, and quota errors before proposing a change.

For OpenCode integrations explicitly requesting this provider, its provider identifier remains `google-vertex`; configure `options.project` and `options.location: "global"`. The workstation's default OpenCode provider is explicitly OpenRouter.

## Primary sources

- [Agent Platform quickstart](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/start) and [product name changes](https://docs.cloud.google.com/gemini-enterprise-agent-platform/vertex-ai-name-changes).
- [Google Gen AI SDK](https://googleapis.github.io/python-genai/) and [SDK releases](https://github.com/googleapis/python-genai/releases).
- [Locations and global endpoint](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/locations).
