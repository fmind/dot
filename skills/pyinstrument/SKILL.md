---
name: pyinstrument
description: Profile Python elapsed time with Pyinstrument. Use for sampling call trees, slow request analysis, async profiling, and HTML performance reports.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/pyinstrument
  created: "2026-09-10"
  updated: "2026-09-10"
---

# Pyinstrument

Use Pyinstrument to locate time spent in a representative Python execution; [memray](../memray/SKILL.md) owns allocations and [benchmark](../benchmark/SKILL.md) owns timing comparisons.

## Workflow

1. Establish a bounded reproducible slow workload and record Python, dependencies, inputs, and the unprofiled runtime. Add `pyinstrument` with `uv add --dev pyinstrument`.
1. Capture the command with `uv run pyinstrument -r html -o profile.html script.py`; use `-m <module>` for a module entry point. Check `uv run pyinstrument --help` for the installed flags.
1. For one request or function, use `Profiler` around only that operation with cleanup in `finally`; choose the async mode deliberately when requests share an event loop.
1. Read the largest elapsed-time branches, separating active work, waits, and framework dispatch. Inspect hidden frames when aggregation obscures the caller; sample intervals can miss very short functions.
1. Change one measured cause, verify behavior, and repeat the same workload. Confirm improvement with an unprofiled benchmark and retain a sanitized report.

## Gotchas

- Sampling measures elapsed time, including waits; it is not an exact invocation counter or a memory profiler.
- Profiles include paths and function names; inspect artifacts before sharing them.
- Profiling overhead and sampling variance can dominate tiny workloads; lengthen a representative run instead of claiming precision from one sample.

## Official Skills

No consumer Agent Skill was found in the inspected [joerick/pyinstrument](https://github.com/joerick/pyinstrument) repository on 2026-09-10. Use the official documentation below; community packages are not upstream endorsements.

## Documentation

- [User guide and CLI](https://pyinstrument.readthedocs.io/en/latest/guide.html) · [API](https://pyinstrument.readthedocs.io/en/latest/reference.html)
