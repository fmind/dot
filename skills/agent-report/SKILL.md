---
name: agent-report
description: "Generate a standalone HTML dashboard report from audit or evaluation evidence and open it in the browser. Use when delivering structured visual reports."
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-report
  created: "2026-09-06"
  updated: "2026-09-06"
---

# Agent Report

Generate a standalone, responsive HTML dashboard report from audit, benchmark, review, or evaluation evidence, save it to `.agents/reports/`, and open it in the local browser.

## Workflow

1. **Collect evidence**: gather verified test outputs, benchmark metrics, or review findings from [repository-review](../repository-review/SKILL.md) or [quality-assurance](../quality-assurance/SKILL.md).
1. **Structure findings**: organize data into an executive summary, steering decisions needed from the developer, and thematic cards with bold key takeaways.
1. **Render HTML**: build a self-contained HTML page using the responsive card layout in [report-template.html](references/report-template.html).
1. **Write locally**: resolve the repository root with `git rev-parse --show-toplevel`; write to `.agents/reports/<YYYY-MM-DD_HH-MM-SS>.html` and copy to `.agents/reports/latest.html`.
1. **Open browser**: when `$DISPLAY` or `$WAYLAND_DISPLAY` is available, launch the desktop browser; otherwise emit the file URI for manual inspection:

```bash
xdg-open .agents/reports/latest.html >/dev/null 2>&1 &
```

1. **Report path**: state the written file path and summarize the top decision needed from the user.

## Gotchas

- **Self-contained markup**: embed all CSS inline; do not rely on remote CDN assets or external scripts so the report works completely offline.
- **Gitignore reports**: keep `.agents/reports/` gitignored; point-in-time machine reports must not pollute repository git status or commit history.
- **Scannable cards**: keep each card focused on 2–4 high-impact bullets with bold keywords; avoid wall-of-text paragraphs.
- **Headless environments**: check display availability before launching; never block or error if browser opening fails in a headless container or remote SSH session.

## Documentation

- Companion skills: [agent-prompt](../agent-prompt/SKILL.md) (continuation prompts), [agent-proposal](../agent-proposal/SKILL.md) (RFC proposals), [repository-review](../repository-review/SKILL.md) (whole-repo audit), [agent-project](../agent-project/SKILL.md) (agent directory layout).
