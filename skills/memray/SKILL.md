---
name: memray
description: Profile Python memory with Memray. Use for allocation stacks, peak usage, native allocations, retained memory, and flamegraph reports.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/memray
  created: "2026-09-10"
  updated: "2026-09-10"
---

# Memray

Use Memray to explain allocation behavior; [pyinstrument](../pyinstrument/SKILL.md) owns elapsed-time call trees and [systematic-debugging](../systematic-debugging/SKILL.md) owns unknown-cause investigation.

## Workflow

1. Reproduce the memory growth with bounded inputs and record process RSS separately. Check platform/wheel support, then add `memray` with `uv add --dev memray`.
1. Capture to a fresh path with `uv run memray run -o capture.bin script.py`; for a module use `uv run memray run -o capture.bin -m package.module`.
1. Inspect `uv run memray stats capture.bin` and `uv run memray flamegraph -o memory.html capture.bin`. Use `--native` on capture when extension allocation stacks matter.
1. Distinguish total allocations, peak live allocations, and allocations retained at capture end; use the relevant reporter options from installed help. Compare equal batches and process lifecycle boundaries.
1. Fix the responsible retention or excessive allocation, verify outputs, and repeat the same capture and unprofiled RSS measurement. Keep reports and binary captures out of normal source control.

## Gotchas

- High allocation volume alone is not a leak; allocator arenas, mapped files, and native libraries can make RSS differ from tracked live memory.
- Native symbol availability and capture options affect attribution. Python allocator tracing adds detail and overhead; enable it for a specific hypothesis.
- Captures can contain paths, stack names, and command details. Use fresh output paths instead of forced overwrites, and review artifacts before sharing.

## Official Skills

No consumer Agent Skill was found in the inspected [bloomberg/memray](https://github.com/bloomberg/memray) repository on 2026-09-10. Use the official documentation below; community packages are not upstream endorsements.

## Documentation

- [Run command](https://bloomberg.github.io/memray/run.html) · [Flamegraphs](https://bloomberg.github.io/memray/flamegraph.html) · [Overview](https://bloomberg.github.io/memray/overview.html)
