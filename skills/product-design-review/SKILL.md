---
name: product-design-review
description: "Review UI/UX: journeys, copy, hierarchy, accessibility, responsive states."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/product-design-review
  created: "2026-08-08"
  updated: "2026-10-05"
---

# Product Design Review

Judge whether a real user can understand, trust, and complete the surface's primary job, then improve only what the requested scope authorizes; [quality-assurance](../quality-assurance/SKILL.md) owns the test campaign and [fmind-visuals](../fmind-visuals/SKILL.md) owns Fmind brand truth.

## Workflow

1. **Recover product truth**: read the brief, existing product or design artifacts, tokens, components, user research, and representative content; name missing evidence, then classify the task as **preserve**, **refine**, or **redesign**.
1. **Map the journey**: entry points, primary action, decisions, exits, failure recovery, and time to first value.
1. **Inspect the live surface**: when a runnable app exists, use [playwright](../playwright/SKILL.md) to capture desktop and mobile states, DOM semantics, console and network errors, keyboard behavior, focus, reduced motion, and screenshots. Otherwise start from committed visual-regression goldens or screenshot fixtures, checked for freshness against current tokens and CSS.
1. **Review comprehension**: information architecture, hierarchy, labels, vocabulary, affordances, progressive disclosure, cognitive load, and whether the next action is obvious.
1. **Review every state**: first run, loading, empty, partial, success, validation, permission, error, offline, destructive confirmation, and recovery.
1. **Review craft**: typography, spacing, alignment, color, contrast, density, imagery, motion, and consistency; flag generic defaults only when they weaken the brief.
1. **Review inclusion**: semantic structure, keyboard access, focus visibility and restoration, touch targets, zoom and reflow, screen-reader names, contrast, motion preferences, localization, and plain-language copy.
1. **Review constraints**: performance, browser, device, content-length, data-density, privacy, and implementation constraints that change the recommendation.
1. **Prioritize**: rank findings `P0`–`P3` (see [repository-review](../repository-review/SKILL.md)) by blocked task, trust or accessibility harm, frequency, and effort; recommend the smallest coherent improvement before aesthetic extras.
1. **Verify authorized changes**: re-run the same representative states at desktop and mobile sizes and record the evidence.

## Gotchas

- **Preserve the established brand**: the brief and established product identity win; do not replace the existing palette or tokens with a personal default.
- **Critiques do not authorize edits**: a critique does not authorize code edits, factual copy changes, or a new visual identity.
- **Prefer one justified signature**: remove elements that do not encode meaning or help the task. Flag common generated tells unless the brief asks for them: uniform rounded cards with identical shadows, ALL-CAPS eyebrow labels, single-word headline accents, middle-dot meta strings, and body lines over ~80 characters.
- **Review real runtime evidence**: review real content, states, and runtime behavior. A static happy-path screenshot is insufficient.
- **Bound the polish loop**: bound iteration to one batched desktop and mobile review, one coherent fix pass when authorized, and one confirmation pass.

## Output

- **Mode and user job**
- **Evidence reviewed** and the critical journey map
- **Findings by severity** with screenshot, state, selector, or source evidence
- **Preserve / change / remove decisions** with the recommended direction, tokens, or interaction rules
- **Accessibility, responsive, and runtime gaps**
- **Next smallest improvement**

## Documentation

- Companion skills: [product-loop](../product-loop/SKILL.md) (what the surface must achieve).
- Adapted from [Anthropic frontend-design](https://github.com/anthropics/skills/blob/41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f/skills/frontend-design/SKILL.md), [Impeccable](https://github.com/pbakaus/impeccable/blob/508d7e8955de3b3caf2d8676e85206723d41a887/.agents/skills/impeccable/SKILL.md), [gstack design-review](https://github.com/garrytan/gstack/blob/960c3a8d6c4d14cb4c5e551a8847f8ec7c4267df/design-review/SKILL.md).
