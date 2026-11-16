---
name: gpu-and-serving
description: "Configure PyTorch CUDA/CPU uv indexes, safetensors loading, and vLLM GPU serving with memory bounds."
---

# GPU PyTorch & Model Serving

Configure reproducible PyTorch wheels with `uv` index routing and run bounded open-weight inference with vLLM on GCE, GKE, or Cloud Run GPU.

## PyTorch via `uv` (`[tool.uv.sources]`)

Route CUDA vs CPU wheels explicitly in `pyproject.toml` so macOS and CPU CI runners lock cleanly alongside Linux GPU boxes without manual `pip install`:

```toml
[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true

[[tool.uv.index]]
name = "pytorch-cu128"
url = "https://download.pytorch.org/whl/cu128"
explicit = true

[tool.uv.sources]
torch = [
  { index = "pytorch-cpu", marker = "sys_platform != 'linux'" },
  { index = "pytorch-cu128", marker = "sys_platform == 'linux'" },
]
```

## Safe Weight Loading & Reproducibility

- **Safetensors & `weights_only=True`**: load weights exclusively from verified `.safetensors` revisions (`hf` pinned SHA commit, never unpinned `main`), pass `weights_only=True` on any `torch.load(...)` fallback, and forbid `trust_remote_code=True` unless audited in place.
- **Headroom before pulls**: run `dot doctor --headroom` before pulling multi-GB checkpoints ([hf](../../hf/SKILL.md)).

## Self-Hosted Serving (`vLLM`)

- **OpenAI-compatible backend**: serve approved open-weight checkpoints with explicit resource bounds (`vllm serve <pinned-model-or-path> --host 127.0.0.1 --port 8000 --max-model-len <N> --gpu-memory-utilization 0.85 --max-num-seqs <N>`) and pair clients with [openai-sdk](../../model-providers/references/openai-sdk.md).
- **Cloud Run / GKE cold starts**: bake or stream verified weights from Artifact Registry / GCS (`run.googleapis.com/gpu-zonal-redundancy-disabled` only when policy permits), set `startup_probe` timeout above load duration, and verify VRAM headroom before raising `--max-model-len`.

## Documentation

- [uv PyTorch guide](https://docs.astral.sh/uv/guides/integration/pytorch/) · [vLLM docs](https://docs.vllm.ai/) · [Safetensors](https://huggingface.co/docs/safetensors/)
