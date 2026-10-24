# Official Skill Sources

Each tool guide's Official Skills section names its maintainer source and selection; this page keeps the gaps and the installation boundaries. Recheck a source before installing because bundles and SDK APIs change independently.

## No official skill found

As of 2026-09-06, no application skill was found in the inspected primary repositories for [Zensical](https://github.com/zensical/zensical), [pytest](https://github.com/pytest-dev/pytest), [structlog](https://github.com/hynek/structlog), [SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy), [Alembic](https://github.com/sqlalchemy/alembic), [HTTPX](https://github.com/encode/httpx), [Granian](https://github.com/emmett-framework/granian), [pdoc](https://github.com/mitmproxy/pdoc), [pydantic-settings](https://github.com/pydantic/pydantic-settings), or [Testcontainers Python](https://github.com/testcontainers/testcontainers-python); the [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk) ships only a contributor test-quality skill. This is a bounded search result, not proof that no maintainer has published guidance elsewhere. Keep official docs and existing project tests as the fallback. Litestar's integration skills do not establish first-party authorship for those underlying libraries.

## Installation boundaries

The personal entry points list the current bundle, review a selected skill, install it from the target project directory without `--global`, and inspect `DISABLE_TELEMETRY=1 skills list`. Preserve the resulting lockfile according to repository policy and check host discovery through [agent-project](../SKILL.md). Do not install an upstream skill that shares a name with a personal wrapper except as the name policy allows; follow the [name policy](vendor-skills.md#name-collisions).

Standalone skills do not install the vendor's full plugin, hooks, MCP servers, language servers, credentials, or cloud resources. Select those separately only when the project needs them. Never treat a contributor-only skill or sample skill as a general library integration simply because it is hosted by the maintainer.
