---
name: google-adk
description: Develop Google Agent Development Kit applications with Agent, Runner, sessions, callbacks, evaluation, and Gemini models. Use for Python google-adk code.
license: MIT
metadata:
  source: github.com/fmind/dot/tree/main/skills/google-adk
  created: "2026-09-02"
  updated: "2026-09-06"
---

# Google ADK

Implement Python ADK behavior within the existing project; [agents-cli](../agents-cli/SKILL.md) owns the generated application, evaluation commands, and deployment lifecycle.

## Workflow

1. **Inspect the installed SDK** and project model, tools, session service, and app entry point before coding. Use [python-stack](../python-stack/SKILL.md) for ordinary Python code.
1. **Choose the official guidance** below for ADK agents, tool functions, orchestration, callbacks, state, or tests; compare its supported SDK version with the project lock.
1. **Implement narrow tools** with complete types, useful docstrings, bounded I/O, and explicit errors. Keep business logic independently testable and prompts in reviewable source.
1. **Test locally** with deterministic tool and workflow cases; run provider smoke calls and repeated evaluations only within their authorized access and cost.
1. **Evaluate changes** with the project or provider's versioned evaluation workflow; preserve generated deployment choices and use [observability](../observability/SKILL.md) for traces.

## Gotchas

- **Framework and generator versions differ**: an SDK can support a Python release the agents-cli scaffold does not; retain the generated constraint until verified compatible.
- **Examples can lag or lead**: compare skill examples with installed dependency source. Keep upstream warnings and prerelease dependency gaps visible.
- **SDK contributor skills have another scope**: repository setup, Git rules, and reflection workflows do not belong in a consumer app merely because Google publishes them.

## Official Skills

For agents-cli projects, use the ADK implementation selection from `google/agents-cli` through [agents-cli](../agents-cli/SKILL.md). For standalone ADK code, `google/adk-python` also publishes application-building guidance alongside contributor and sample skills. Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md), choose the application skill and required references, and verify its version assumptions against the locked ADK dependency.

## Documentation

- [ADK docs](https://google.github.io/adk-docs/) · [Python SDK](https://github.com/google/adk-python) · [Google CLI and skills](https://github.com/google/agents-cli)
- Companion skills: [agents-cli](../agents-cli/SKILL.md), [prompt-design](../prompt-design/SKILL.md), [quality-assurance](../quality-assurance/SKILL.md), [python-stack](../python-stack/SKILL.md).
