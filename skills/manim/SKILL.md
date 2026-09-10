---
name: manim
description: Create mathematical animations with Manim Community. Use for scenes, equations, transformations, camera motion, and reproducible video renders.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/manim
  created: "2026-09-10"
  updated: "2026-09-10"
---

# Manim

Use the Manim Community `manim` package for Python-authored animations; keep the visual explanation understandable without relying on motion alone.

## Workflow

1. Identify Community Edition versus ManimGL before editing; inspect `manim.cfg`, Python dependencies, fonts, and the selected renderer. Add `manim` with `uv add manim` for Community projects.
1. Plan the scene's teaching point, objects, timing, aspect ratio, and final frame. Implement a named `Scene` subclass with `construct()`, explicit imports, and deterministic inputs.
1. Start with geometry or `Text`; introduce `MathTex` only when a compatible TeX toolchain is available. Check the platform installation guide for native dependencies before a build.
1. Render one low-quality scene with `uv run manim -ql scene.py SceneName`. Inspect representative frames and the video for clipped labels, overlap, contrast, and pacing.
1. Render the accepted scene with `uv run manim -qh scene.py SceneName`; deliver the source, configuration, and output path. Re-render after changing fonts, dimensions, or equations.

## Gotchas

- ManimGL (`manimlib`) examples are not interchangeable with Community imports and renderer behavior.
- TeX, Pango, Cairo, and rendering support vary with platform and release; a successful Python install alone does not prove rendering readiness.
- Preview flags open external applications; omit them in headless automation. A completed render still needs visual inspection.

## Official Skills

No consumer Agent Skill was found in the inspected [ManimCommunity/manim](https://github.com/ManimCommunity/manim) repository on 2026-09-10. Use the official documentation below; community packages are not upstream endorsements.

## Documentation

- [Quickstart](https://docs.manim.community/en/stable/tutorials/quickstart.html) · [Installation](https://docs.manim.community/en/stable/installation.html) · [Configuration](https://docs.manim.community/en/stable/guides/configuration.html)
