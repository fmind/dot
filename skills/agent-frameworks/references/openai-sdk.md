---
name: openai-sdk
description: "Async OpenAI Responses API, Workload Identity, and strict Pydantic outputs."
---

# OpenAI Python SDK (`3.51.0+`)

Use `openai` (`AsyncOpenAI`) directly on OpenAI-compatible workloads or OpenAI API integrations; prefer [OpenRouter](openrouter.md) when routing across multiple open/proprietary vendors via `OPENAI_API_KEY`.

## Workflow

1. **Authenticate safely**: use `AsyncOpenAI(..., workload_identity=...)` where federated OIDC identity applies, or pass short-lived/scoped keys via `with-secret` / secret manager; configure explicit timeouts and retries (`http_client=httpx2.AsyncClient(...)` or SDK defaults).
1. **Default to the Responses API (`client.responses`)**: prefer `await client.responses.parse(...)` over legacy `chat.completions` for structured outputs and reasoning models:
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
1. **Zero-retention & strict tools**: default `store=False` unless server-side response state is explicitly authorized, mark function tools `strict: true` (`additionalProperties: false` via Pydantic schemas), bound max output/tool calls (`max_output_tokens`, `max_tool_calls`), and fail closed when `parsed is None` (refusal or truncation).

## Documentation

- [OpenAI Python SDK](https://github.com/openai/openai-python) · [Responses API guide](https://developers.openai.com/api/reference/resources/responses) · [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
