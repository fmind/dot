# Official Skill Sources

Checked 2026-09-06 against the managed mise tools, the dot Python dependencies, and the Python, agent, web, data, and telemetry skill references. Sources below are maintainer repositories, not marketplace rankings. Repository trees and selected skill bodies were inspected; discovery was exercised with `skills add ... --list` for the new Python routes. Recheck before installing because bundles and SDK APIs change independently.

## Python and documentation

| Tool | Verified source and capability | Personal entry point |
| --- | --- | --- |
| Zensical | [zensical/zensical](https://github.com/zensical/zensical): no authoring skill in the inspected tree; official docs and CLI bootstrap/build tested with 0.0.59 | [zensical](../../zensical/SKILL.md), the default documentation/course publisher |
| Agents CLI | [google/agents-cli](https://github.com/google/agents-cli): application lifecycle, scaffold, ADK code, evaluation, deployment, publishing, observability | [agents-cli](../../agents-cli/SKILL.md) |
| Google ADK | [google/adk-python](https://github.com/google/adk-python/tree/a119dd7751082dbbd9a65f71e359abdc2be659cc/.agents/skills): agent-building guidance plus separate SDK contributor and sample workflows | [google-adk](../../google-adk/SKILL.md); select application guidance only |
| Pydantic | [pydantic/skills](https://github.com/pydantic/skills/tree/9e9390ee24d44b32cf5379c58acaebd7563f5f86/skills): validation, Pydantic AI, and Logfire | [pydantic](../../pydantic/SKILL.md); agent and telemetry products are optional |
| Litestar | [litestar-org/litestar-skills](https://github.com/litestar-org/litestar-skills/tree/84587b4ccb97e31e34230f800d4dc2f90f6ae11d/skills): web framework guidance and optional ecosystem libraries | [litestar](../../litestar/SKILL.md) |
| Typer | [fastapi/typer](https://github.com/fastapi/typer/tree/82b83959d9e900215ed8ff2a56a766ff066e1c75/typer/.agents/skills): official CLI authoring guidance shipped inside the source package | [typer](../../typer/SKILL.md) |
| FastAPI | [fastapi/fastapi](https://github.com/fastapi/fastapi/tree/50113da16fec53b66b80d75e80a89296de4fa5a5/fastapi/.agents/skills): official API framework guidance, relevant to the agents-cli scaffold | [fastapi](../../fastapi/SKILL.md); preserve Litestar as the ordinary web default |
| uv, Ruff, ty | [astral-sh/claude-code-plugins](https://github.com/astral-sh/claude-code-plugins/tree/f3ce88a7ba830f53afd6d944c1d0278ed318e142/plugins/astral/skills): three standalone tool skills, also packaged as a Claude plugin | [uv](../../uv/SKILL.md), [ruff](../../ruff/SKILL.md), [ty](../../ty/SKILL.md) |
| Python MCP | [anthropics/skills](https://github.com/anthropics/skills/tree/41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f/skills/mcp-builder): Anthropic's MCP builder includes Python guidance; this is not a Python SDK maintainer skill | [mcp-server](../../mcp-server/SKILL.md), with installed-SDK API verification |
| Python A2A | [a2aproject/a2a-python](https://github.com/a2aproject/a2a-python/tree/57a9df3e2bd79a4b6d889e17511f789baa038dac): only a repository-specific mistake-reflection skill was found | Use official SDK docs and [technical-research](../../technical-research/SKILL.md); no vendor installer invented |

The [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk/tree/08a3bc8eaf5bb69a6cb05ac708a86f5325977c20) contains a contributor test-quality skill, not a consumer SDK tutorial. The [A2A CLI specification](https://github.com/a2aproject/a2a-cli) describes optional Agent Skills distribution but the inspected tree ships no `SKILL.md`; protocol `AgentSkill` objects on Agent Cards are a different concept.

No application skill was found in the inspected primary repositories for [pytest](https://github.com/pytest-dev/pytest), [structlog](https://github.com/hynek/structlog), [SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy), [Alembic](https://github.com/sqlalchemy/alembic), [HTTPX](https://github.com/encode/httpx), [Granian](https://github.com/emmett-framework/granian), [pdoc](https://github.com/mitmproxy/pdoc), [pydantic-settings](https://github.com/pydantic/pydantic-settings), or [Testcontainers Python](https://github.com/testcontainers/testcontainers-python). This is a bounded search result, not proof that no maintainer has published guidance elsewhere. Keep official docs and existing project tests as the fallback. Litestar's integration skills do not establish first-party authorship for those underlying libraries.

## Existing routes for other key tools

These maintainer repositories contain skills and already have personal entry points; retain them instead of adding duplicate wrappers.

| Ecosystem | Official source | Existing entry point |
| --- | --- | --- |
| Antigravity Python SDK | [Google-Antigravity/antigravity-sdk-python](https://github.com/Google-Antigravity/antigravity-sdk-python) | [antigravity-sdk](../../antigravity-sdk/SKILL.md) |
| Google Cloud and developer products | [google/skills](https://github.com/google/skills) | [google-cloud](../../google-cloud/SKILL.md), [google-developer](../../google-developer/SKILL.md) |
| Workspace | [googleworkspace/cli](https://github.com/googleworkspace/cli) | [gws](../../gws/SKILL.md) |
| Colab | [googlecolab/google-colab-cli](https://github.com/googlecolab/google-colab-cli) | [colab](../../colab/SKILL.md) |
| Hugging Face | [huggingface/skills](https://github.com/huggingface/skills) | [hf](../../hf/SKILL.md) |
| Kaggle | [Kaggle/kaggle-cli](https://github.com/Kaggle/kaggle-cli), [Kaggle/kaggle-skills](https://github.com/Kaggle/kaggle-skills) | [kaggle](../../kaggle/SKILL.md) |
| DuckDB | [duckdb/duckdb-skills](https://github.com/duckdb/duckdb-skills) | [duckdb](../../duckdb/SKILL.md) |
| AST search | [ast-grep/agent-skill](https://github.com/ast-grep/agent-skill) | [ast-grep](../../ast-grep/SKILL.md) |
| Browser tools | [ChromeDevTools/chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp), [microsoft/playwright-cli](https://github.com/microsoft/playwright-cli) | [chrome-devtools](../../chrome-devtools/SKILL.md), [playwright](../../playwright/SKILL.md); CLI guidance is not the Python Playwright API |
| Web platform | [GoogleChrome/modern-web-guidance](https://github.com/GoogleChrome/modern-web-guidance) | [modern-web](../../modern-web/SKILL.md) |
| Infrastructure | [hashicorp/agent-skills](https://github.com/hashicorp/agent-skills) | [terraform](../../terraform/SKILL.md); verify OpenTofu compatibility |
| Telemetry and evaluations | [langfuse/skills](https://github.com/langfuse/skills), [mlflow/skills](https://github.com/mlflow/skills), [pydantic/skills](https://github.com/pydantic/skills), [grafana/skills](https://github.com/grafana/skills) | [observability](../../observability/SKILL.md); select the project's actual backend |

## Installation boundaries

The personal entry points list the current bundle, review a selected skill, install it from the target project directory without `--global`, and inspect `skills list`. Preserve the resulting lockfile according to repository policy and check host discovery through [agent-project](../../agent-project/SKILL.md). An upstream skill may share a name with the personal wrapper: preserve local customizations and let the project installation supply the vendor detail.

Standalone skills do not install the vendor's full plugin, hooks, MCP servers, language servers, credentials, or cloud resources. Select those separately only when the project needs them. Never treat a contributor-only skill or sample skill as a general library integration simply because it is hosted by the maintainer.
