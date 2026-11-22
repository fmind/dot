---
name: gpu-and-serving
description: "PyTorch CUDA/CPU uv indexes, safetensors, and bounded vLLM GPU serving."
---

# GPU PyTorch & Model Serving

Configure reproducible PyTorch wheels with `uv` index routing and run bounded open-weight inference with vLLM on GCE, GKE, or Cloud Run GPU.

## PyTorch via `uv` (`[tool.uv.sources]`)

Route CUDA vs CPU wheels explicitly in `pyproject.toml` so non-Linux dev machines (macOS/Windows) lock CPU wheels alongside Linux GPU hosts without manual `pip install` (when Linux CPU CI runners must also stay on CPU wheels, declare mutually exclusive `cpu`/`cu128` extras with `[tool.uv] conflicts`):

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
- **Inference-mode parity & determinism**: wrap PyTorch inference in `model.eval()` and `with torch.inference_mode():` (prevents dropout/BatchNorm skew and autograd leaks), pass explicit `torch.Generator` seeds for sampling/dataloaders, and use `torch.amp.autocast("cuda", dtype=torch.bfloat16)` for mixed precision on Ampere+ GPUs.
- **Headroom before pulls**: run `dot doctor --headroom` before pulling multi-GB checkpoints ([hf](../../cloud-ops/references/hf.md)).

## Self-Hosted Serving (`vLLM`)

- **OpenAI-compatible backend**: serve approved open-weight checkpoints with explicit resource bounds (`vllm serve <pinned-model-or-path> --host 127.0.0.1 --port 8000 --max-model-len <N> --gpu-memory-utilization 0.85 --max-num-seqs <N>`) and pair clients with [openai-sdk](../../agent-frameworks/references/openai-sdk.md).
- **Cloud Run / GKE cold starts**: bake or stream verified weights from Artifact Registry / GCS (`run.googleapis.com/gpu-zonal-redundancy-disabled` only when policy permits), set `startup_probe` timeout above load duration, and verify VRAM headroom before raising `--max-model-len`.

## Documentation

- [uv PyTorch guide](https://docs.astral.sh/uv/guides/integration/pytorch/) · [vLLM docs](https://docs.vllm.ai/) · [Safetensors](https://huggingface.co/docs/safetensors/)
