---
name: agy
description: "Operate Antigravity's agy CLI, headless reviews, Remote Control, statusline, settings, and SDK."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agy
  created: "2026-09-09"
  updated: "2026-11-17"
---

# Agy

Operate Antigravity via its CLI or Python SDK; load every matching guide and linked resource needed to complete and verify the workflow.

## Task guides

<!-- guides:start -->

- [antigravity-sdk](references/antigravity-sdk/GUIDE.md): Python SDK orchestration, policy, subagents, and lifecycle.
- [cli](references/cli/GUIDE.md): CLI sessions, managed settings and auth, custom agents, and completions.
- [headless-review](references/headless-review/GUIDE.md): Run a structured headless agy review with JSON schema and fail-closed exit checks.
- [remote-control](references/remote-control.md): Run agy Remote Control: per-session tunnels, headless daemon, and project registry.
- [statusline](references/statusline.md): Change or diagnose the managed agy status line and terminal title renderer.

<!-- guides:end -->

## Documentation

- [CLI reference](https://antigravity.google/docs/cli/reference/) · [Python SDK](https://antigravity.google/docs/sdk/overview/) · [Remote Control](https://antigravity.google/docs/remote-control/) · [Changelog](https://antigravity.google/docs/changelog)
- Companions: [agent-harnesses](../agent-harnesses/SKILL.md), [task-prompts](../task-prompts/SKILL.md), [subagent](../subagent/SKILL.md), [dot-cli](../dot-cli/SKILL.md).
