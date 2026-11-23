# Local and OpenAI-Compatible Models

Run local or self-hosted models with `google-antigravity` ([docs](https://antigravity.google/docs/sdk/local-models/)); `agy` CLI `customModelsConfig` (`gemini-api://<base_url>/models/<model>`) works only under `modelProvider: "gemini"`, never subscription auth.

- **`LiteRTAgentConfig(model_path=...)`**: runs `.litertlm` on-device (`backend`: `gpu` default, `npu`, `cpu`) with `.lightweight()`, automatic multi-turn KV prefix caching, thought-channel streaming, and `token_threshold=40960` compaction (64k KV cache) applied. `0.1.24+` (with `litert-lm >= 0.19.1`) auto-detects on-device vision (`vision_backend` override `"gpu"`/`"cpu"`). Expand `~` manually on `model_path` and `cache_dir` (and `mkdir` `cache_dir` first). Gemma 4 26B A4B needs ~16.8 GB disk and ~24 GB VRAM/unified memory (`dot doctor --headroom` first).
- **`LocalOpenAIAgentConfig(model=..., base_url=...)`**: targets Ollama/LM Studio/vLLM (not `litert-lm serve`); chain `.lightweight()` for small models (`0.1.24+` populates streaming token `Usage`/latency, honors `Retry-After` on 429/5xx, and surfaces non-200 HTTP errors as `AntigravityConnectionError`):

```python
config = LocalOpenAIAgentConfig(
    model="gemma4:26b",
    base_url="http://localhost:11434/v1",
    workspaces=[workspace],
).lightweight()
```

Verified through `0.1.24`: `LocalOpenAIAgentConfig` carries no `api_key`/auth field and posts `{base_url}/chat/completions` without an `Authorization` header even when `OPENAI_API_KEY` is set. Front authenticated remote endpoints with a loopback proxy (e.g., LiteLLM) injecting credentials via `with-secret` or secret manager, and test tool calls + `response_schema` in a scratch workspace first.
