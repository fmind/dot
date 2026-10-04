---
name: google-adk
description: "Google ADK agents, runners, tools, sessions, and evaluation."
---

# Google ADK

Implement Python ADK behavior within the existing project; [agents-cli](agents-cli/GUIDE.md) owns the generated application, evaluation commands, and deployment lifecycle.

## Workflow

1. **Inspect the installed SDK** and project model, tools, session service, and app entry point before coding. Use [python-stack](../../python-stack/references/foundation/GUIDE.md) for shared project defaults only when needed; preserve the generated layout.
1. **Choose the official guidance** below for ADK agents, tool functions, orchestration, callbacks, state, or tests; compare its supported SDK version with the project lock.
1. **Set the runtime contract**: choose one agent unless the workflow requires orchestration; make the model, provider authentication, session persistence, run limits, and timeout explicit. Keep the runner and session service consistent on app, user, and session IDs.
1. **Wire narrow tools explicitly**: in the generated layout, `app/agent.py` defines `root_agent`; tools have complete type signatures, useful docstrings, bounded I/O, and explicit errors, while business logic stays in independently testable modules and prompts in reviewable source. Enforce authorization and idempotency in the tool boundary rather than relying on model instructions; offline tests inspect agent wiring and call tool functions directly.
1. **Handle events and state**: consume the runner event stream, distinguish tool calls and errors from a final response, and handle empty or non-text parts. Update state through tool/callback context or service events so the selected session service can persist deltas.
1. **Test locally** with deterministic tool cases and a fake model or event stream; cover invalid inputs, tool failures, final response extraction, and isolation between two user sessions; run provider smoke calls and repeated evaluations only within their authorized access and cost.
1. **Evaluate changes** through the [agents-cli](agents-cli/GUIDE.md) evaluation workflow or the project's own, preserving generated deployment choices; [observability](../../observability/SKILL.md) owns traces.

## Gotchas

- **State scope**: unprefixed state is session-scoped; `user:` shares across the user's sessions, `app:` across users, and `temp:` is invocation-local. Keep sensitive per-user data out of app state; in-memory session storage does not survive restart.
- **Callbacks can change control flow**: verify the installed callback signature and return semantics; test both the continue and short-circuit paths.
- **Framework and generator versions differ**: an SDK can support a Python release the agents-cli scaffold does not; retain the generated constraint until verified compatible.
- **Examples can lag or lead**: compare skill examples with installed dependency source. Keep upstream warnings and prerelease dependency gaps visible.
- **SDK contributor skills have another scope**: repository setup, Git rules, and reflection workflows do not belong in a consumer app merely because Google publishes them.

## Official Skills

For agents-cli projects, use the ADK implementation selection from `google/agents-cli` through [agents-cli](agents-cli/GUIDE.md). For standalone ADK code, [google/adk-python application skills](https://github.com/google/adk-python/tree/main/.agents/skills) also publishes `adk-agent-builder`, its one application-building skill, alongside contributor and sample skills. Discover with `skills add google/adk-python --list`. Follow the shared [vendor-skill policy](../../agent-project/references/vendor-skills.md), select `adk-agent-builder` and its required references, and verify its version assumptions against the locked ADK dependency.

## Documentation

- [Session state](https://adk.dev/sessions/state/) · [Runtime](https://adk.dev/runtime/)
- [ADK docs](https://adk.dev/) · [Python SDK](https://github.com/google/adk-python) · [Google CLI and skills](https://github.com/google/agents-cli)
- Releases: [adk-python](https://github.com/google/adk-python/releases) · [changelog](https://github.com/google/adk-python/blob/main/CHANGELOG.md)
- Companion skills: [agents-cli](agents-cli/GUIDE.md), [prompt-design](../../prompt-design/SKILL.md), [quality-assurance](../../quality-assurance/SKILL.md), [python-stack](../../python-stack/references/foundation/GUIDE.md).
