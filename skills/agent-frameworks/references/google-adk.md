---
name: google-adk
description: "Google ADK agents, runners, tools, sessions, and evaluation."
---

# Google ADK

Implement Python ADK agents inside the project; [agents-cli](agents-cli/GUIDE.md) owns scaffolding, evaluation commands, and deployment.

## Workflow

1. **Inspect first**: check the locked SDK, model, tools, session service, and entry point; apply [python-stack](../../python-stack/references/foundation/GUIDE.md) defaults without altering generated layout.
1. **Match SDK version**: verify upstream skill assumptions against the locked ADK version.
1. **Set the runtime contract**: use a single agent unless orchestration is needed; otherwise build a graph `Workflow` (`google.adk.workflow`)—ADK 2 deprecates `SequentialAgent`, `ParallelAgent`, and `LoopAgent` (`Workflow` cannot yet be an `LlmAgent` sub-agent). Align app, user, and session IDs across runner and session service.
1. **Wire narrow tools**: define `root_agent` in `app/agent.py`; give tools full type hints, clear docstrings, bounded I/O, explicit errors, and code-enforced authorization/idempotency while keeping business logic in testable modules and prompts in source.
1. **Handle events and state**: consume the runner event stream (separating tool calls, errors, empty/non-text parts, and final responses) and mutate state via tool/callback context or service events so deltas persist.
1. **Test and evaluate**: test tool functions and two-user session isolation offline with fake models/streams; run live smoke calls and [agents-cli](agents-cli/GUIDE.md) evaluations only within authorized access and budget; wire traces per [observability](../../python-stack/references/observability.md).

## Gotchas

- **State prefixes set scope**: unprefixed is session-scoped, `user:` spans a user's sessions, `app:` spans users, and `temp:` is invocation-local. Keep user secrets/PII out of `app:`; in-memory sessions reset on restart.
- **Callbacks alter control flow**: verify installed signatures and test both continue and short-circuit returns.
- **Generator vs SDK Python range**: keep the `agents-cli` Python constraint until verified compatible.
- **ADK 2.13 span rename**: telemetry defaults to OTel GenAI semconv 1.44 and drops `call_llm`; update queries/dashboards or set `ADK_TELEMETRY_SCHEMA_VERSION_OPT_IN=otel_semconv_1_36` during migration.
- **Skip contributor skills**: do not install upstream repo-maintenance or sample skills into consumer apps.

## Official Skills

Use `google/agents-cli` skills via [agents-cli](agents-cli/GUIDE.md), or for standalone ADK discover [google/adk-python skills](https://github.com/google/adk-python/tree/main/.agents/skills) (`adk-agent-builder`, `adk-debug`) with `DISABLE_TELEMETRY=1 skills add google/adk-python --list --json` per [vendor-skill policy](../../agent-project/references/vendor-skills.md).

## Documentation

- [Session state](https://adk.dev/sessions/state/) · [Runtime](https://adk.dev/runtime/) · [Workflows](https://adk.dev/workflows/)
- [ADK docs](https://adk.dev/) · [Python SDK](https://github.com/google/adk-python) · [Google CLI and skills](https://github.com/google/agents-cli)
- Releases: [adk-python](https://github.com/google/adk-python/releases) · [changelog](https://github.com/google/adk-python/blob/main/CHANGELOG.md)
- Companion skills: [agents-cli](agents-cli/GUIDE.md), [evaluation](evaluation/GUIDE.md), [python-stack](../../python-stack/references/foundation/GUIDE.md).
