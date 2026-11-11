# PyRIT Execution

Baseline: [PyRIT 1.1.0](https://github.com/microsoft/PyRIT/tree/d0524f0714840519b826eb770687ca1d4f46a761) (Python 3.10–3.14). Check installed `.venv` source before adopting APIs from `latest` docs, and run CLI + Python code from the same locked `uv` project (a global CLI is not importable).

## Prepare a project

```bash
uv init --python 3.14
UV_MALWARE_CHECK=1 uv add --preview-features malware-check 'pyrit==1.1.0'
uv run --locked python -c 'from importlib.metadata import version; print(version("pyrit"))'
uv run --locked pyrit_scan --help
uv run --locked pyrit_scan run --help
```

Set target, attacker model, and scorer explicitly (all three can receive prompts/outputs); load credentials from env/secret stores only, and audit default env files and initializers before running.

## Local library smoke

Verify package wiring offline in a clean temp `HOME` with no credentials (imports may still create cache/log dirs):

```python
import asyncio
import io

from pyrit.memory import CentralMemory
from pyrit.models import Message
from pyrit.prompt_target import TextTarget
from pyrit.setup import IN_MEMORY, initialize_pyrit_async


async def main() -> None:
    await initialize_pyrit_async(
        memory_db_type=IN_MEMORY,
        load_defaults=False,
        env_files=[],
        env_akv_ref=[],
        silent=True,
    )
    stream = io.StringIO()
    target = TextTarget(text_stream=stream)
    try:
        response = await target.send_prompt_async(
            message=Message.from_prompt(prompt="synthetic-assessment-marker", role="user")
        )
        assert response == []
        assert "synthetic-assessment-marker" in stream.getvalue()
    finally:
        await target.cleanup_target_async()
        CentralMemory.get_memory_instance().dispose_engine()


asyncio.run(main())
```

Custom 1.1.0 targets implement `_send_prompt_to_target_async` (keeping `send_prompt_async` validation intact); start with single-turn `PromptSendingAttack` before multi-turn strategies.

## CLI and campaign lifecycle

`pyrit_scan` (1.1.0) is a REST client: `list-scenarios`, `list-targets`, and `run` require a running backend (which can run initializers and persist state; only `--help` is offline). Pass explicit `--server-url` and `--config-file`; `--max-dataset-size`, `--max-concurrency`, and `--max-retries` do not cap total spend or wall time, and `--request-timeout` bounds client wait only. On timeout/disconnect, check `scenario-history` and `scenario-results` before retrying, stop only assessment-owned backends, and pair PyRIT scores with application action traces rather than text-only scoring.

Sources: [installation](https://microsoft.github.io/PyRIT/latest/getting-started/readme/) · [CLI](https://github.com/microsoft/PyRIT/blob/d0524f0714840519b826eb770687ca1d4f46a761/pyrit/cli/pyrit_scan.py) · [initialization](https://github.com/microsoft/PyRIT/blob/d0524f0714840519b826eb770687ca1d4f46a761/pyrit/setup/initialization.py) · [target contract](https://github.com/microsoft/PyRIT/blob/d0524f0714840519b826eb770687ca1d4f46a761/pyrit/prompt_target/common/prompt_target.py).
