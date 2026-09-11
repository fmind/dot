# PyRIT Execution

The verified baseline is [PyRIT 1.1.0](https://github.com/microsoft/PyRIT/tree/d0524f0714840519b826eb770687ca1d4f46a761), whose package supports Python 3.10 through 3.14. Read installed source or the matching release before using APIs from the evolving `latest` documentation. The global mise tool exposes the CLI; importable assessment code belongs in its own `uv` project and lockfile.

## Prepare a project

In the assessment project, add the selected version to its existing dependency group and commit the resulting lockfile when committing is authorized. For a new assessment environment:

```bash
uv init --python 3.14
uv add 'pyrit==1.1.0'
uv run --locked python -c 'from importlib.metadata import version; print(version("pyrit"))'
uv run --locked pyrit_scan --help
uv run --locked pyrit_scan run --help
```

Choose the target, attacker model, and scorer explicitly. A local runner can still send content to all three providers. Use approved endpoints and environment-based credentials; keep secrets out of committed configuration and command arguments. Review which default environment files or initializers will load before starting a run.

## Local library smoke

Run this in a disposable assessment environment with an empty home/data directory and no provider credentials. It exercises PyRIT message validation and a local text target without a model, server, or scorer. Imports can create PyRIT cache/log directories even with in-memory conversation storage.

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

This proves local package wiring only. Build an application-specific target and independent outcome checks before claiming security coverage. In 1.1.0, custom targets implement `_send_prompt_to_target_async`; preserve the public `send_prompt_async` validation/normalization path. Use the released `PromptSendingAttack` for fixed single-turn cases and select multi-turn strategies only after the adapter and scorer are verified.

## CLI and campaign lifecycle

The 1.1.0 `pyrit_scan` CLI is a REST client. Commands such as `list-scenarios`, `list-targets`, and `run` require a backend; they are not offline discovery commands. Use `--help` for offline inspection. Starting a backend can load initializers, register targets, and create persistent state: inspect the selected configuration and destination first.

Use explicit `--server-url` and `--config-file` values for an established backend. Inspect `list-targets` and `list-scenarios` there, then select the scenario, target, techniques, and datasets. `run --help` documents `--max-dataset-size`, `--max-concurrency`, and `--max-retries`; these do not collectively enforce a campaign cost or wall-time limit. Keep the outer limits in the assessment project's runner and the provider/application controls.

`--request-timeout` bounds the client's wait, not necessarily the server's work. On disconnect or timeout, reconcile the run with `scenario-history` and `scenario-results` before retrying. Stop only the backend and operations owned by this assessment. Preserve partial results and classify interrupted or unevaluated cases explicitly.

Record the application's action trace alongside PyRIT's conversation and scoring results. Do not use a text-only score to establish tenant isolation or a completed tool effect. Preserve the original failure as a regression, then compare retests using the same case and execution budgets.

Sources: [installation](https://microsoft.github.io/PyRIT/latest/getting-started/readme/), [released CLI](https://github.com/microsoft/PyRIT/blob/d0524f0714840519b826eb770687ca1d4f46a761/pyrit/cli/pyrit_scan.py), [initialization](https://github.com/microsoft/PyRIT/blob/d0524f0714840519b826eb770687ca1d4f46a761/pyrit/setup/initialization.py), and [target contract](https://github.com/microsoft/PyRIT/blob/d0524f0714840519b826eb770687ca1d4f46a761/pyrit/prompt_target/common/prompt_target.py).
