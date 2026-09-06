---
name: python-stack
description: Build typed Python projects with uv, Ruff, ty, pytest, Litestar, and Typer. Use for packages, CLIs, web apps, agents, tests, or typing.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/python-stack
  created: "2026-06-23"
  updated: "2026-09-05"
---

# Python Stack Standard

Use typed Python for packages, CLIs, Litestar applications, and ADK integrations. [python-script](../python-script/SKILL.md) owns single-file PEP 723 scripts; [google-adk](../google-adk/SKILL.md) owns the agent workflow.

## Defaults

- **Toolchain**: stable Python managed by uv; lock dependencies in `uv.lock` and keep `.python-version` aligned with `requires-python`.
- **Quality**: Ruff for code formatting/lint, ty for types, pytest for behavior, and dprint for markup/config. Keep checks warning-free.
- **Tests**: deterministic offline tests by default; the starter's branch-coverage target is 85%, adapted to the project. Database/provider integrations require their declared environment.
- **Boundaries**: Pydantic/settings for external input and configuration; structlog for readable local output and JSON production logs; no manual virtual environments.

## Workflow

1. **Choose the profile**: inspect existing conventions, then select library, CLI, data/ML, web, or agent from [profiles](references/profiles.md).
1. **Scaffold only when needed**: follow [bootstrap](references/bootstrap.md), preserving project-specific configuration and using the matching files below.
1. **Implement and verify**: use project-local tools through `uv run` and canonical mise tasks; run focused tests, then the required gate.
1. **Finish**: synchronize human and agent docs through [update-docs](../update-docs/SKILL.md); report proof and leave commits to the authorized scope.

## References by task

| Need                                        | Read                                                                                                                                                                           |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Version, configuration, and tooling details | [tooling.md](references/tooling.md), [pyproject.toml.template](references/pyproject.toml.template), [mise.toml](references/mise.toml), [lefthook.yml](references/lefthook.yml) |
| Project conventions and environment         | [AGENTS.md](references/AGENTS.md), [env.example](references/env.example), [gitignore](references/gitignore)                                                                    |
| Library                                     | [init-library.py](references/init-library.py), [test_library.py](references/test_library.py)                                                                                   |
| CLI and shared entry point                  | [init-cli.py](references/init-cli.py), [main.py](references/main.py), [test_smoke.py](references/test_smoke.py), [test_cli.py](references/test_cli.py)                         |
| Web and explicit database integration       | [init.py](references/init.py), [test_web.py](references/test_web.py), [conftest.py](references/conftest.py), [test_integration.py](references/test_integration.py)             |

## Gotchas

- **Inspect source**: locate distributions with `uv pip show` and read their files; importing a module to inspect it can execute code.
- **Names**: distribution/command slugs can contain hyphens; Python imports and package directories use underscores.
- **Provider calls**: generated agent integration tests can make paid calls; replace dummy tests with meaningful local behavior and separate live checks.

## Official Skills

Astral's `astral-sh/claude-code-plugins` provides Python-tool integrations. Discover the current bundle with native host tooling and select only the required integration.

## Documentation

- [Python](https://docs.python.org/3/) · [uv](https://docs.astral.sh/uv/) · [Ruff](https://docs.astral.sh/ruff/) · [ty](https://docs.astral.sh/ty/) · [Litestar](https://docs.litestar.dev/) · [pytest](https://docs.pytest.org/)
- Companion skills: [google-adk](../google-adk/SKILL.md) (agents), [python-script](../python-script/SKILL.md), [cli-contracts](../cli-contracts/SKILL.md), [containerize](../containerize/SKILL.md), [github-actions](../github-actions/SKILL.md), [secure](../secure/SKILL.md).
