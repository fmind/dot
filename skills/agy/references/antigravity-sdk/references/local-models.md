# Local and OpenAI-Compatible Models

Run local or self-hosted models with `google-antigravity` ([docs](https://antigravity.google/docs/sdk/local-models/)); `agy` CLI `customModelsConfig` (`gemini-api://<base_url>/models/<model>`) works only under `modelProvider: "gemini"`, never subscription auth.

- **`LiteRTAgentConfig(model_path=...)`**: runs `.litertlm` on-device (`backend`: `gpu` default, `npu`, `cpu`) with `.lightweight()` applied; Gemma 4 26B A4B needs ~16.8 GB disk and ~24 GB VRAM/unified memory (`dot doctor --headroom` first).
- **`LocalOpenAIAgentConfig(model=..., base_url=...)`**: targets Ollama/LM Studio/vLLM (not `litert-lm serve`); chain `.lightweight()` for small models:

```python
config = LocalOpenAIAgentConfig(
    model="gemma4:26b",
    base_url="http://localhost:11434/v1",
    workspaces=[workspace],
).lightweight()
```

Verified in 0.1.20 against a loopback fake (2026-10-03): the harness posts `{base_url}/chat/completions` without an `Authorization` header even when `OPENAI_API_KEY` is set (`GemmaEndpoint` / `ModelTarget` carry no auth fields). Front authenticated remote endpoints with a loopback proxy (e.g., LiteLLM) injecting credentials via `dot secret run` or secret manager, and test tool calls + `response_schema` in a scratch workspace first.
